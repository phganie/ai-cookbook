import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def download_youtube_audio(url: str, temp_dir: Path | None = None) -> tuple[Path, Path]:
    """
    Download YouTube audio using yt-dlp.
    
    Args:
        url: YouTube video URL
        temp_dir: Optional temporary directory. If None, creates a new one.
    
    Returns:
        Tuple of (temp_directory_path, audio_file_path)
        The caller is responsible for cleanup of the temp directory.
    """
    logger.info("Downloading audio for URL: %s", url)
    
    # Create temp directory if not provided
    if temp_dir is None:
        temp_dir_obj = tempfile.TemporaryDirectory()
        temp_dir = Path(temp_dir_obj.name)
        # Note: We return the Path, but the TemporaryDirectory will be cleaned up
        # when it goes out of scope. For production use, we'll manage cleanup explicitly.
    else:
        temp_dir = Path(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Use yt-dlp to download audio only
    # Prefer mp3, fallback to m4a or best audio format
    output_template = str(temp_dir / "%(id)s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "192K",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "-o", output_template,
        url,
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        logger.info("Audio download completed successfully")
        
        # Find the downloaded file
        # yt-dlp outputs the filename, but we can also search for it
        audio_files = list(temp_dir.glob("*.mp3"))
        if not audio_files:
            # Try other formats
            audio_files = list(temp_dir.glob("*.m4a"))
        if not audio_files:
            audio_files = list(temp_dir.glob("*.*"))
        
        if not audio_files:
            raise ValueError("No audio file found after download")
        
        audio_path = audio_files[0]
        logger.info("Downloaded audio file: %s (size: %d bytes)", audio_path, audio_path.stat().st_size)
        
        return temp_dir, audio_path
        
    except subprocess.TimeoutExpired:
        logger.error("Audio download timed out after 5 minutes")
        raise RuntimeError("Audio download timed out") from None
    except subprocess.CalledProcessError as e:
        logger.error("yt-dlp failed: %s", e.stderr)
        raise RuntimeError(f"Failed to download audio: {e.stderr}") from e
    except Exception as e:
        logger.exception("Unexpected error during audio download")
        raise RuntimeError(f"Audio download failed: {str(e)}") from e

