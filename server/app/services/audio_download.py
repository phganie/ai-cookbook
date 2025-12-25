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