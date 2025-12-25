import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from ..config import get_settings
from .audio_download import download_youtube_audio
from .stt import transcribe_audio_google
from .video_metadata import get_video_metadata
from .youtube import extract_youtube_video_id, get_youtube_transcript

logger = logging.getLogger(__name__)

TranscriptSource = Literal["captions", "audio", "metadata"]

# Simple in-memory cache for transcripts (cleared on restart)
_transcript_cache: dict[str, tuple[str, list[dict] | None, TranscriptSource]] = {}


def _vtt_to_text(vtt: str) -> str:
    """Convert VTT subtitle format to plain text, stripping timestamps and tags."""
    lines = []
    for line in vtt.splitlines():
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line:
            continue
        # Remove tags like <c> ... </c>
        line = re.sub(r"<[^>]+>", "", line)
        # Remove speaker labels or timestamps if any
        if re.fullmatch(r"\d+", line):
            continue
        lines.append(line)
    # De-dupe and clean whitespace
    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_captions_via_ytdlp(url: str) -> str | None:
    """
    Fetch captions using yt-dlp with --skip-download (no audio download).
    This is production-safe and avoids YouTube bot detection.
    
    Returns plain text transcript if available, None otherwise.
    """
    temp_dir_obj = None
    try:
        temp_dir_obj = tempfile.TemporaryDirectory()
        temp_dir = Path(temp_dir_obj.name)
        temp_dir.mkdir(parents=True, exist_ok=True)
        out_tpl = str(temp_dir / "%(id)s.%(ext)s")

        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs", "en.*,en",
            "--sub-format", "vtt",
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            "-o", out_tpl,
            url,
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        except subprocess.CalledProcessError as e:
            logger.warning("yt-dlp captions failed: %s", (e.stderr or "").strip())
            return None
        except Exception as e:
            logger.warning("Captions fetch error: %s", e)
            return None

        # Find VTT files
        vtts = list(temp_dir.glob("*.vtt"))
        if not vtts:
            logger.debug("No VTT files found in temp directory")
            return None

        # Read first VTT file and convert to text
        vtt_content = vtts[0].read_text(encoding="utf-8", errors="ignore")
        text = _vtt_to_text(vtt_content)
        return text if text else None

    except Exception as e:
        logger.warning("Error in get_captions_via_ytdlp: %s", e)
        return None
    finally:
        if temp_dir_obj:
            try:
                temp_dir_obj.cleanup()
            except Exception as cleanup_error:
                logger.debug("Failed to cleanup temp files: %s", cleanup_error)


def get_transcript_with_fallback(url: str) -> tuple[str, list[dict] | None, TranscriptSource]:
    """
    Get transcript with production-safe fallback order:
    1. Try yt-dlp captions (--skip-download, no audio)
    2. Try metadata-based generation (title/description)
    3. Try audio transcription ONLY if ENABLE_AUDIO_TRANSCRIPTION=true
    
    Results are cached in memory to avoid re-processing the same video.
    
    Args:
        url: YouTube video URL
    
    Returns:
        Tuple of (transcript_text, segments_or_none, source)
        - transcript_text: The transcript as a string
        - segments_or_none: Caption segments if from captions, None otherwise
        - source: "captions", "metadata", or "audio"
    
    Raises:
        ValueError: If no transcript available and metadata fallback also fails
    """
    # Check cache first
    video_id = extract_youtube_video_id(url)
    if video_id and video_id in _transcript_cache:
        logger.info("Using cached transcript for video_id=%s", video_id)
        return _transcript_cache[video_id]
    
    settings = get_settings()
    
    # Step 1: Try yt-dlp captions first (production-safe, no audio download)
    logger.info("Attempting yt-dlp captions extraction (no audio download)")
    ytdlp_captions = get_captions_via_ytdlp(url)
    if ytdlp_captions and ytdlp_captions.strip():
        logger.info("Successfully retrieved transcript from yt-dlp captions: %d characters", len(ytdlp_captions))
        result = (ytdlp_captions, None, "captions")
        if video_id:
            _transcript_cache[video_id] = result
        return result
    
    logger.debug("yt-dlp captions not available, trying youtube-transcript-api")
    
    # Step 2: Try youtube-transcript-api as fallback (may work when yt-dlp doesn't)
    try:
        transcript_text, segments = get_youtube_transcript(url)
        logger.info("Successfully retrieved transcript from youtube-transcript-api")
        result = (transcript_text, segments, "captions")
        if video_id:
            _transcript_cache[video_id] = result
        return result
    except Exception as captions_error:
        logger.warning("youtube-transcript-api captions failed: %s", captions_error)
    
    # Step 3: Try metadata fallback (no audio download, production-safe)
    logger.info("Captions unavailable, attempting metadata-based recipe generation")
    try:
        metadata = get_video_metadata(url)
        if metadata and metadata.title:
            # Return a placeholder transcript using the video title
            # This will be handled specially in the LLM call
            placeholder_text = f"Video title: {metadata.title}"
            if metadata.description:
                placeholder_text += f"\nDescription: {metadata.description}"
            result = (placeholder_text, None, "metadata")
            if video_id:
                _transcript_cache[video_id] = result
            logger.info("Metadata fallback successful, using video title: %s", metadata.title)
            return result
        else:
            logger.warning("Metadata fallback failed: no metadata or title available")
    except Exception as metadata_error:
        logger.warning("Metadata fallback failed: %s", metadata_error)
    
    # Step 4: Try audio transcription ONLY if explicitly enabled
    if not settings.enable_audio_transcription:
        logger.info("Audio transcription disabled (ENABLE_AUDIO_TRANSCRIPTION=false), skipping audio fallback")
        raise ValueError("NO_TRANSCRIPT_AVAILABLE")
    
    # Check if we have required config for STT
    if not settings.gcp_project_id:
        logger.error("GCP_PROJECT_ID not set, cannot use audio transcription")
        raise ValueError("NO_TRANSCRIPT_AVAILABLE")
    
    # Attempt audio transcription (local dev only)
    logger.info("Attempting audio transcription fallback (ENABLE_AUDIO_TRANSCRIPTION=true)")
    temp_dir_obj = None
    try:
        # Create temporary directory for audio download
        temp_dir_obj = tempfile.TemporaryDirectory()
        temp_dir = Path(temp_dir_obj.name)
        
        # Download audio
        audio_dir, audio_path = download_youtube_audio(url, temp_dir)
        logger.info("Audio downloaded: %s", audio_path)
        
        # Check file size (rough guardrail)
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        # Rough estimate: 1MB per minute
        estimated_duration = file_size_mb * 60
        
        if estimated_duration > settings.stt_max_audio_seconds:
            raise ValueError(
                f"Audio too long (estimated {estimated_duration:.0f}s, max {settings.stt_max_audio_seconds}s)"
            )
        
        # Transcribe
        transcript_text = transcribe_audio_google(
            file_path=audio_path,
            project_id=settings.gcp_project_id,
            location=settings.gcp_location,
            language_code=settings.stt_language_code,
            model=settings.stt_model,
            max_audio_seconds=settings.stt_max_audio_seconds,
        )
        
        if not transcript_text or not transcript_text.strip():
            raise RuntimeError("Transcription returned empty result")
        
        logger.info("Successfully transcribed audio: %d characters", len(transcript_text))
        result = (transcript_text, None, "audio")
        # Cache the result
        if video_id:
            _transcript_cache[video_id] = result
        return result
        
    except Exception as audio_error:
        logger.exception("Audio transcription fallback failed: %s", audio_error)
        # If audio fails, we've already tried metadata, so raise
        raise ValueError("NO_TRANSCRIPT_AVAILABLE") from audio_error
    finally:
        # Clean up temporary files
        if temp_dir_obj:
            try:
                temp_dir_obj.cleanup()
                logger.debug("Cleaned up temporary audio files")
            except Exception as cleanup_error:
                logger.warning("Failed to cleanup temp files: %s", cleanup_error)

