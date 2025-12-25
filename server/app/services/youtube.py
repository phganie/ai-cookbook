import logging
from typing import List, Tuple
from urllib.parse import parse_qs, urlparse

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from ..config import get_settings

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
        except Exception as exc:
            logger.info(
                "Manual transcript not found for video_id=%s langs=%s err=%s",
                video_id,
                langs,
                type(exc).__name__,
            )

    # Then try generated English
    for langs in (["en-US", "en"], ["en"]):
        try:
            return tl.find_generated_transcript(langs).fetch()
        except Exception as exc:
            logger.info(
                "Generated transcript not found for video_id=%s langs=%s err=%s",
                video_id,
                langs,
                type(exc).__name__,
            )

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

    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as exc:
        logger.exception(
            "Transcript unavailable for video_id=%s error_type=%s msg=%s",
            video_id, type(exc).__name__, str(exc)
        )
        raise ValueError(f"NO_TRANSCRIPT_AVAILABLE:{type(exc).__name__}") from exc

    except Exception as exc:
        logger.exception(
            "Transcript fetch failed for video_id=%s error_type=%s msg=%s",
            video_id, type(exc).__name__, str(exc)
        )
        raise


def get_captions_via_youtube_api(video_id: str) -> str | None:
    """
    Fetch captions using YouTube Data API v3 (official API).
    Requires YOUTUBE_API_KEY to be set.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Plain text transcript if available, None otherwise
    """
    settings = get_settings()
    
    if not settings.youtube_api_key:
        logger.debug("YOUTUBE_API_KEY not set, skipping YouTube Data API v3")
        return None
    
    try:
        # Build YouTube API client
        youtube = build('youtube', 'v3', developerKey=settings.youtube_api_key)
        
        # List available captions for the video
        captions_response = youtube.captions().list(
            part='snippet',
            videoId=video_id
        ).execute()
        
        if not captions_response.get('items'):
            logger.debug("No captions found via YouTube Data API v3 for video_id=%s", video_id)
            return None
        
        # Find English caption (prefer manually created, then auto-generated)
        caption_id = None
        for caption in captions_response['items']:
            lang = caption['snippet'].get('language', '')
            if lang.startswith('en'):
                if caption['snippet'].get('trackKind') == 'standard':
                    # Prefer manually created
                    caption_id = caption['id']
                    break
                elif not caption_id:
                    # Fallback to auto-generated
                    caption_id = caption['id']
        
        if not caption_id:
            # Use first available caption
            caption_id = captions_response['items'][0]['id']
        
        # Download the caption track
        # The download method returns the caption content directly
        caption_request = youtube.captions().download(
            id=caption_id,
            tfmt='srt'  # SRT format is easier to parse
        )
        
        # Execute the request - returns bytes
        caption_bytes = caption_request.execute()
        
        # Decode bytes to string
        caption_text = caption_bytes.decode('utf-8') if isinstance(caption_bytes, bytes) else str(caption_bytes)
        
        # Parse SRT format to extract text
        # SRT format: number, timestamp, text, blank line
        lines = caption_text.split('\n')
        text_lines = []
        skip_next = False
        
        for line in lines:
            line = line.strip()
            if not line:
                skip_next = False
                continue
            if skip_next:
                continue
            # Check if line is a number (sequence number)
            if line.isdigit():
                skip_next = True  # Skip timestamp line next
                continue
            # Check if line is a timestamp (contains -->)
            if '-->' in line:
                continue
            # This should be the text
            text_lines.append(line)
        
        transcript_text = ' '.join(text_lines).strip()
        
        if transcript_text:
            logger.info("Successfully retrieved transcript via YouTube Data API v3: %d characters", len(transcript_text))
            return transcript_text
        else:
            logger.warning("YouTube Data API v3 returned empty transcript for video_id=%s", video_id)
            return None
            
    except HttpError as e:
        error_details = e.error_details[0] if e.error_details else {}
        reason = error_details.get('reason', 'unknown')
        
        if reason == 'quotaExceeded':
            logger.warning("YouTube Data API v3 quota exceeded")
        elif reason == 'forbidden':
            logger.warning("YouTube Data API v3 access forbidden (check API key permissions)")
        else:
            logger.warning("YouTube Data API v3 error: %s (reason: %s)", e, reason)
        return None
    except Exception as e:
        logger.warning("YouTube Data API v3 failed for video_id=%s: %s", video_id, e)
        return None