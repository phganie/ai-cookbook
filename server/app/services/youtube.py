import logging
from typing import List, Tuple

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

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
        logger.error("No transcript found for video %s and transcription fallback is disabled", video_id)
        raise ValueError(
            f"No transcript available for video {video_id}. "
            "Please ensure the video has captions enabled, or use a different video."
        )




