import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

def _vtt_to_text(vtt: str) -> str:
    lines = []
    for line in vtt.splitlines():
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line:
            continue
        # remove tags like <c> ... </c>
        line = re.sub(r"<[^>]+>", "", line)
        # remove speaker labels or timestamps if any
        if re.fullmatch(r"\d+", line):
            continue
        lines.append(line)
    # de-dupe a bit
    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def fetch_youtube_captions(url: str, temp_dir: Path) -> str | None:
    """
    Fetch captions (manual or auto) without downloading audio.
    Returns plain text transcript if available.
    """
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
        # If YouTube blocks even this, you'll see similar bot error in stderr
        logger.warning("yt-dlp captions failed: %s", (e.stderr or "").strip())
        return None
    except Exception as e:
        logger.warning("Captions fetch error: %s", e)
        return None

    vtts = list(temp_dir.glob("*.vtt"))
    if not vtts:
        return None

    vtt = vtts[0].read_text(encoding="utf-8", errors="ignore")
    text = _vtt_to_text(vtt)
    return text or None


def download_youtube_audio(url: str, temp_dir: Path) -> tuple[Path, Path]:
    """
    Download YouTube audio using yt-dlp.
    
    Args:
        url: YouTube video URL
        temp_dir: Temporary directory to save audio file
    
    Returns:
        Tuple of (audio_dir, audio_path) where:
        - audio_dir: Directory containing the audio file
        - audio_path: Path to the downloaded audio file
    
    Raises:
        RuntimeError: If download fails
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_tpl = str(temp_dir / "%(id)s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "m4a",  # Use m4a for better compatibility
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "-o", out_tpl,
        url,
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        logger.debug("Audio download completed successfully")
    except subprocess.CalledProcessError as e:
        error_msg = (e.stderr or "").strip()
        logger.error("yt-dlp audio download failed: %s", error_msg)
        raise RuntimeError(f"Failed to download audio: {error_msg}") from e
    except subprocess.TimeoutExpired:
        logger.error("yt-dlp audio download timed out")
        raise RuntimeError("Audio download timed out") from None
    except Exception as e:
        logger.error("Unexpected error during audio download: %s", e)
        raise RuntimeError(f"Failed to download audio: {str(e)}") from e
    
    # Find the downloaded audio file
    audio_files = list(temp_dir.glob("*.m4a"))
    if not audio_files:
        # Try other common audio formats
        for ext in ["mp3", "webm", "opus"]:
            audio_files = list(temp_dir.glob(f"*.{ext}"))
            if audio_files:
                break
    
    if not audio_files:
        raise RuntimeError("Downloaded audio file not found")
    
    audio_path = audio_files[0]
    logger.info("Downloaded audio file: %s (size: %d bytes)", audio_path, audio_path.stat().st_size)
    
    return temp_dir, audio_path