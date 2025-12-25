import logging
from typing import List, Tuple
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)


def extract_youtube_video_id(url: str) -> str | None:
    """Extract video id from watch?v=, youtu.be/, and /shorts/ URLs."""
    parsed = urlparse(url)

    # youtu.be/VIDEO_ID
    if parsed.netloc in ("youtu.be", "www.youtu.be"):
        vid = parsed.path.lstrip("/")
        return vid or None

    # youtube.com/watch?v=VIDEO_ID
    qs = parse_qs(parsed.query or "")
    if "v" in qs and qs["v"]:
        return qs["v"][0]

    # youtube.com/shorts/VIDEO_ID
    if "youtube.com" in parsed.netloc and parsed.path.startswith("/shorts/"):
        rest = parsed.path.split("/shorts/", 1)[1]
        vid = rest.split("/", 1)[0]
        return vid or None

    return None


def _pick_transcript(video_id: str) -> List[dict]:
    """Pick the best available transcript segments for a video."""
    tl = YouTubeTranscriptApi.list_transcripts(video_id)

    # Prefer manually created English variants first
    for langs in (["en-US", "en"], ["en"]):
        try:
            return tl.find_transcript(langs).fetch()
        except Exception:
            pass

    # Then try generated English
    for langs in (["en-US", "en"], ["en"]):
        try:
            return tl.find_generated_transcript(langs).fetch()
        except Exception:
            pass

    # Fallback: first available transcript in any language
    return next(iter(tl)).fetch()


def get_youtube_transcript(url: str) -> Tuple[str, List[dict]]:
    video_id = extract_youtube_video_id(url)
    if not video_id:
        raise ValueError("Could not parse YouTube video id from URL")

    logger.info("Fetching transcript for video_id=%s", video_id)

    try:
        logger.info("TRANSCRIPT_PICKER_V2 enabled for video_id=%s", video_id)
        transcript = _pick_transcript(video_id)
        text = " ".join(chunk.get("text", "") for chunk in transcript).strip()
        if not text:
            raise ValueError("Transcript was empty")
        return text, transcript

    except Exception as exc:
        logger.error("Transcript not available for video %s: %s", video_id, exc)
        raise ValueError(
            f"No transcript available for video {video_id}. "
            "Try a different video, or add an audio-to-text fallback."
        ) from exc