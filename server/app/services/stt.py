import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------- Audio helpers ----------

def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def convert_to_wav_16k_mono(src: Path, dst: Path) -> Path:
    """
    Convert to WAV PCM 16kHz mono (Speech v1 friendly).
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(dst),
    ]
    _run(cmd)
    return dst


def get_duration_seconds(path: Path) -> float:
    """
    Use ffprobe to get accurate duration in seconds.
    """
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def slice_wav(input_wav: Path, start_s: float, dur_s: float, out_wav: Path) -> Path:
    """
    Cut a WAV segment [start_s, start_s+dur_s).
    """
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_s),
        "-t", str(dur_s),
        "-i", str(input_wav),
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(out_wav),
    ]
    _run(cmd)
    return out_wav


# ---------- STT ----------

def transcribe_audio_google(
    file_path: Path,
    project_id: str,          # kept for signature compatibility
    location: str,            # kept for signature compatibility
    language_code: str = "en-US",
    model: Optional[str] = None,
    max_audio_seconds: int = 600,
) -> str:
    """
    Robust v1 transcription:
    - Convert to wav 16k mono
    - Chunk into 55s segments
    - Transcribe each chunk and concatenate
    """
    from google.cloud import speech

    logger.info("Transcribing audio via v1 (chunked): %s", file_path)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        wav_path = td / "audio.wav"

        convert_to_wav_16k_mono(file_path, wav_path)

        total_sec = get_duration_seconds(wav_path)
        logger.info("Audio duration: %.2fs", total_sec)

        # hard cap (optional)
        if total_sec > max_audio_seconds:
            logger.warning(
                "Audio %.1fs exceeds max_audio_seconds=%s. Transcribing only first %ss.",
                total_sec, max_audio_seconds, max_audio_seconds
            )
            total_sec = float(max_audio_seconds)

        CHUNK_SEC = 55.0

        client = speech.SpeechClient()

        # v1: don’t force "latest_long" (can cause INVALID_ARGUMENT)
        config_kwargs = dict(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language_code,
            enable_automatic_punctuation=True,
        )
        # Only include model if you KNOW a v1-valid model string
        if model:
            config_kwargs["model"] = model

        config = speech.RecognitionConfig(**config_kwargs)

        parts: list[str] = []
        start = 0.0
        idx = 0

        while start < total_sec:
            dur = min(CHUNK_SEC, total_sec - start)
            chunk_path = td / f"chunk_{idx:04d}.wav"
            slice_wav(wav_path, start, dur, chunk_path)

            audio = speech.RecognitionAudio(content=chunk_path.read_bytes())

            logger.info("STT chunk %d: start=%.1fs dur=%.1fs", idx, start, dur)

            # recognize should be fine for 55s chunks
            resp = client.recognize(config=config, audio=audio)

            for r in resp.results:
                if r.alternatives:
                    parts.append(r.alternatives[0].transcript)

            start += dur
            idx += 1

        transcript = " ".join(p.strip() for p in parts if p.strip()).strip()
        logger.info("Transcription done. chars=%d", len(transcript))
        return transcript