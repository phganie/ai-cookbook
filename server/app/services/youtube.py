import io
import logging
import subprocess
import tempfile
from typing import List, Tuple

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

from ..config import get_settings

logger = logging.getLogger(__name__)


def extract_youtube_video_id(url: str) -> str | None:
    # Very simple extraction; can be improved.
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    return None


def get_youtube_transcript(url: str) -> Tuple[str, List[dict]]:
    video_id = extract_youtube_video_id(url)
    if not video_id:
        raise ValueError("Could not parse YouTube video id from URL")

    logger.info("Fetching transcript for video_id=%s", video_id)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(chunk["text"] for chunk in transcript)
        return text, transcript
    except NoTranscriptFound:
        logger.warning("No transcript found for video %s; falling back to audio + Whisper", video_id)
        return transcribe_with_whisper(url)


def transcribe_with_whisper(url: str) -> Tuple[str, List[dict]]:
    """
    Fallback: use yt-dlp to download audio and Whisper to transcribe.
    Returns raw text and a simple list of {text, start, end} segments.
    """
    import whisper  # lazy import

    settings = get_settings()

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = f"{tmpdir}/audio.m4a"
        ytdlp_cmd = [
            "yt-dlp",
            "-x",
            "--audio-format",
            "m4a",
            "-o",
            audio_path,
            url,
        ]
        if settings.youtube_cookie:
            ytdlp_cmd.extend(["--cookies", settings.youtube_cookie])

        logger.info("Downloading audio with yt-dlp")
        subprocess.check_call(ytdlp_cmd)

        logger.info("Transcribing audio with Whisper (small)")
        model = whisper.load_model("small")
        result = model.transcribe(audio_path)

        segments = []
        for seg in result.get("segments", []):
            segments.append(
                {
                    "text": seg.get("text", ""),
                    "start": float(seg.get("start", 0.0)),
                    "end": float(seg.get("end", 0.0)),
                }
            )

        full_text = " ".join(seg["text"] for seg in segments)
        return full_text, segments


