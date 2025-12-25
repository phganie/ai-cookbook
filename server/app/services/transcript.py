import logging
import tempfile
from pathlib import Path
from typing import Literal

from ..config import get_settings
from .audio_download import download_youtube_audio
from .stt import transcribe_audio_google
from .youtube import get_youtube_transcript

logger = logging.getLogger(__name__)

TranscriptSource = Literal["captions", "audio"]


def get_transcript_with_fallback(url: str) -> tuple[str, list[dict] | None, TranscriptSource]:
    """
    Get transcript with audio fallback.
    
    Tries captions first. If that fails and ENABLE_AUDIO_FALLBACK=1,
    downloads audio and transcribes via Google Speech-to-Text.
    
    Args:
        url: YouTube video URL
    
    Returns:
        Tuple of (transcript_text, segments_or_none, source)
        - transcript_text: The transcript as a string
        - segments_or_none: Caption segments if from captions, None if from audio
        - source: "captions" or "audio"
    
    Raises:
        ValueError: If captions fail and fallback is disabled
        RuntimeError: If audio fallback fails
    """
    settings = get_settings()
    
    # Try captions first
    try:
        transcript_text, segments = get_youtube_transcript(url)
        logger.info("Successfully retrieved transcript from captions")
        return transcript_text, segments, "captions"
    except Exception as captions_error:
        logger.warning("Captions failed: %s", captions_error)
        
        # Check if fallback is enabled
        if not settings.enable_audio_fallback:
            logger.error("Audio fallback disabled, cannot proceed")
            raise ValueError("NO_TRANSCRIPT_AVAILABLE") from captions_error
        
        # Check if we have required config for STT
        if not settings.gcp_project_id:
            logger.error("GCP_PROJECT_ID not set, cannot use audio fallback")
            raise ValueError("NO_TRANSCRIPT_AVAILABLE") from captions_error
        
        # Attempt audio fallback
        logger.info("Attempting audio transcription fallback")
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
            return transcript_text, None, "audio"
            
        except Exception as audio_error:
            logger.exception("Audio transcription fallback failed")
            raise RuntimeError("AUDIO_TRANSCRIPTION_FAILED") from audio_error
        finally:
            # Clean up temporary files
            if temp_dir_obj:
                try:
                    temp_dir_obj.cleanup()
                    logger.debug("Cleaned up temporary audio files")
                except Exception as cleanup_error:
                    logger.warning("Failed to cleanup temp files: %s", cleanup_error)

