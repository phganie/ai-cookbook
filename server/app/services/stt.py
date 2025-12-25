import concurrent.futures
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
    Optimized v1 transcription with parallel processing:
    - Convert to wav 16k mono
    - For short videos (< 60s): use long_running_recognize (faster)
    - For longer videos: chunk into 55s segments and process in parallel
    """
    from google.cloud import speech

    logger.info("Transcribing audio via v1 (optimized): %s", file_path)

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

        client = speech.SpeechClient()

        # v1: don't force "latest_long" (can cause INVALID_ARGUMENT)
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

        # For short videos, use long_running_recognize (faster, no chunking overhead)
        if total_sec <= 60:
            logger.info("Using long_running_recognize for short video (%.1fs)", total_sec)
            audio = speech.RecognitionAudio(content=wav_path.read_bytes())
            operation = client.long_running_recognize(config=config, audio=audio)
            response = operation.result(timeout=300)

            parts = []
            for result in response.results:
                if result.alternatives:
                    parts.append(result.alternatives[0].transcript)

            transcript = " ".join(p.strip() for p in parts if p.strip()).strip()
            logger.info("Transcription done. chars=%d", len(transcript))
            return transcript

        # For longer videos, use parallel chunk processing
        # Use 55s chunks to stay under the synchronous recognize limit (60s is too close to the limit)
        CHUNK_SEC = 55.0
        logger.info("Using parallel chunk processing for long video (%.1fs)", total_sec)

        def transcribe_chunk(chunk_info: tuple[int, float, float]) -> tuple[int, str]:
            """Transcribe a single chunk. Returns (chunk_index, transcript)."""
            idx, start, dur = chunk_info
            chunk_path = td / f"chunk_{idx:04d}.wav"
            
            # Slice the chunk
            slice_wav(wav_path, start, dur, chunk_path)
            
            # Create audio object
            audio = speech.RecognitionAudio(content=chunk_path.read_bytes())
            
            logger.info("STT chunk %d: start=%.1fs dur=%.1fs", idx, start, dur)
            
            # Use long_running_recognize for chunks >= 55s to avoid "Sync input too long" error
            # The synchronous recognize method has a limit around 55-58 seconds
            if dur >= 55.0:
                logger.info("Using long_running_recognize for chunk %d (duration %.1fs >= 55s)", idx, dur)
                operation = client.long_running_recognize(config=config, audio=audio)
                response = operation.result(timeout=300)  # 5 minute timeout
                transcript = ""
                for r in response.results:
                    if r.alternatives:
                        transcript += r.alternatives[0].transcript + " "
            else:
                # Use synchronous recognize for shorter chunks (faster)
                resp = client.recognize(config=config, audio=audio)
                transcript = ""
                for r in resp.results:
                    if r.alternatives:
                        transcript += r.alternatives[0].transcript + " "
            
            return idx, transcript.strip()

        # Create chunk tasks
        chunk_tasks = []
        start = 0.0
        idx = 0
        while start < total_sec:
            dur = min(CHUNK_SEC, total_sec - start)
            chunk_tasks.append((idx, start, dur))
            start += dur
            idx += 1

        # Process chunks in parallel (max 6 workers for better throughput)
        # Using 6 workers should give ~3-4x speedup for 8 chunks
        parts_dict = {}
        max_workers = min(6, len(chunk_tasks))
        logger.info("Processing %d chunks in parallel with %d workers", len(chunk_tasks), max_workers)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(transcribe_chunk, task): task[0] for task in chunk_tasks}
            for future in concurrent.futures.as_completed(futures):
                try:
                    chunk_idx, transcript = future.result()
                    parts_dict[chunk_idx] = transcript
                except Exception as e:
                    logger.error("Chunk transcription failed: %s", e)
                    # Continue with other chunks

        # Reassemble in order
        parts = [parts_dict[i] for i in sorted(parts_dict.keys()) if parts_dict[i]]
        transcript = " ".join(p.strip() for p in parts if p.strip()).strip()
        logger.info("Transcription done. chars=%d", len(transcript))
        return transcript