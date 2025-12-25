"""
Service to fetch YouTube video metadata (thumbnail, author, date, etc.)
"""
import json
import logging
import subprocess
from datetime import datetime
from typing import Optional

from .youtube import extract_youtube_video_id

logger = logging.getLogger(__name__)


class VideoMetadata:
    """Video metadata from YouTube."""
    
    def __init__(
        self,
        video_id: str,
        title: str,
        thumbnail_url: str,
        author: str,
        upload_date: Optional[str] = None,
        duration: Optional[int] = None,
        description: Optional[str] = None,
    ):
        self.video_id = video_id
        self.title = title
        self.thumbnail_url = thumbnail_url
        self.author = author
        self.upload_date = upload_date
        self.duration = duration
        self.description = description


def get_video_metadata(url: str) -> Optional[VideoMetadata]:
    """
    Fetch video metadata using yt-dlp.
    Returns None if metadata cannot be fetched.
    """
    video_id = extract_youtube_video_id(url)
    if not video_id:
        logger.warning("Could not extract video ID from URL: %s", url)
        return None
    
    try:
        # Use yt-dlp to get video info as JSON
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            "--quiet",
            url,
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode != 0:
            logger.warning("yt-dlp failed for video_id=%s: %s", video_id, result.stderr)
            return None
        
        data = json.loads(result.stdout)
        
        # Extract relevant fields
        thumbnail_url = data.get("thumbnail") or data.get("thumbnails", [{}])[0].get("url", "")
        author = data.get("uploader") or data.get("channel", "") or "Unknown"
        upload_date = data.get("upload_date")  # Format: YYYYMMDD
        duration = data.get("duration")  # in seconds
        description = data.get("description") or ""  # Video description
        
        # Format upload date if available
        formatted_date = None
        if upload_date:
            try:
                # Parse YYYYMMDD format
                dt = datetime.strptime(upload_date, "%Y%m%d")
                formatted_date = dt.strftime("%B %d, %Y")
            except Exception:
                formatted_date = upload_date
        
        return VideoMetadata(
            video_id=video_id,
            title=data.get("title", "Untitled"),
            thumbnail_url=thumbnail_url,
            author=author,
            upload_date=formatted_date,
            duration=duration,
            description=description,
        )
        
    except subprocess.TimeoutExpired:
        logger.warning("yt-dlp timeout for video_id=%s", video_id)
        return None
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse yt-dlp JSON for video_id=%s: %s", video_id, e)
        return None
    except Exception as e:
        logger.warning("Error fetching metadata for video_id=%s: %s", video_id, e)
        return None

