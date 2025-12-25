import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def transcribe_audio_google(
    file_path: Path,
    project_id: str,
    location: str,
    language_code: str = "en-US",
    model: str | None = None,
    max_audio_seconds: int = 600,
) -> str:
    """
    Transcribe audio file using Google Cloud Speech-to-Text.
    
    Uses v2 API if available, falls back to v1.
    Automatically uses long_running_recognize for audio > 60 seconds.
    
    Args:
        file_path: Path to audio file
        project_id: GCP project ID
        location: GCP location (e.g., "us-central1")
        language_code: Language code (e.g., "en-US")
        model: Optional model name (e.g., "latest_long")
        max_audio_seconds: Maximum audio duration in seconds (guardrail)
    
    Returns:
        Concatenated transcript text
    """
    logger.info(
        "Transcribing audio: %s (project=%s, location=%s, language=%s)",
        file_path,
        project_id,
        location,
        language_code,
    )
    
    # Read audio file
    audio_bytes = file_path.read_bytes()
    file_size_mb = len(audio_bytes) / (1024 * 1024)
    logger.info("Audio file size: %.2f MB", file_size_mb)
    
    # Try to use v2 API first (google-cloud-speech v2)
    try:
        return _transcribe_v2(
            audio_bytes=audio_bytes,
            project_id=project_id,
            location=location,
            language_code=language_code,
            model=model,
            max_audio_seconds=max_audio_seconds,
        )
    except ImportError:
        logger.info("Speech-to-Text v2 not available, falling back to v1")
        return _transcribe_v1(
            audio_bytes=audio_bytes,
            project_id=project_id,
            location=location,
            language_code=language_code,
            model=model,
            max_audio_seconds=max_audio_seconds,
        )


def _transcribe_v2(
    audio_bytes: bytes,
    project_id: str,
    location: str,
    language_code: str,
    model: str | None,
    max_audio_seconds: int,
) -> str:
    """Transcribe using Speech-to-Text v2 API."""
    from google.cloud import speech_v2
    from google.cloud.speech_v2 import RecognitionConfig, RecognitionFeatures
    
    client = speech_v2.SpeechClient()
    
    # Build recognition config
    config = RecognitionConfig(
        auto_decoding_config={},  # Auto-detect encoding
        language_codes=[language_code],
        model=model or "latest_long",
        features=RecognitionFeatures(
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
        ),
    )
    
    # Build request
    request = speech_v2.RecognizeRequest(
        recognizer=f"projects/{project_id}/locations/{location}/recognizers/_",
        config=config,
        content=audio_bytes,
    )
    
    # For long audio, use long_running_recognize
    # Estimate duration: assume ~1MB per minute for typical audio
    estimated_duration = len(audio_bytes) / (1024 * 1024) * 60
    
    if estimated_duration > 60 or len(audio_bytes) > 10 * 1024 * 1024:  # > 60s or > 10MB
        logger.info("Using long-running recognition (estimated duration: %.1f seconds)", estimated_duration)
        operation = client.long_running_recognize(request=request)
        response = operation.result(timeout=300)  # 5 minute timeout
    else:
        logger.info("Using synchronous recognition")
        response = client.recognize(request=request)
    
    # Extract transcript
    transcript_parts = []
    for result in response.results:
        for alternative in result.alternatives:
            transcript_parts.append(alternative.transcript)
    
    transcript = " ".join(transcript_parts).strip()
    logger.info("Transcription completed: %d characters", len(transcript))
    
    return transcript


def _transcribe_v1(
    audio_bytes: bytes,
    project_id: str,
    location: str,
    language_code: str,
    model: str | None,
    max_audio_seconds: int,
) -> str:
    """Transcribe using Speech-to-Text v1 API (fallback)."""
    from google.cloud import speech
    
    client = speech.SpeechClient()
    
    # Build recognition config
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        sample_rate_hertz=16000,  # Common default
        language_code=language_code,
        model=model or "latest_long",
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True,
    )
    
    audio = speech.RecognitionAudio(content=audio_bytes)
    
    # Estimate duration for long-running recognition
    estimated_duration = len(audio_bytes) / (1024 * 1024) * 60
    
    if estimated_duration > 60 or len(audio_bytes) > 10 * 1024 * 1024:
        logger.info("Using long-running recognition (estimated duration: %.1f seconds)", estimated_duration)
        operation = client.long_running_recognize(config=config, audio=audio)
        response = operation.result(timeout=300)
    else:
        logger.info("Using synchronous recognition")
        response = client.recognize(config=config, audio=audio)
    
    # Extract transcript
    transcript_parts = []
    for result in response.results:
        for alternative in result.alternatives:
            transcript_parts.append(alternative.transcript)
    
    transcript = " ".join(transcript_parts).strip()
    logger.info("Transcription completed: %d characters", len(transcript))
    
    return transcript

