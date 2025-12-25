"""
Tests for transcript service with audio fallback.
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.transcript import get_transcript_with_fallback
from app.services.youtube import get_youtube_transcript


class TestTranscriptFallback:
    """Test transcript fallback logic."""

    @patch("app.services.transcript.get_youtube_transcript")
    def test_captions_success(self, mock_get_transcript):
        """Test successful captions retrieval."""
        # Mock the actual function to return tuple
        mock_get_transcript.return_value = ("Hello world", [{"text": "Hello", "start": 0.0}])
        
        text, segments, source = get_transcript_with_fallback("https://youtube.com/watch?v=test")
        
        assert text == "Hello world"
        assert segments is not None
        assert source == "captions"

    @patch("app.services.transcript.get_youtube_transcript")
    @patch("app.services.transcript.get_settings")
    def test_fallback_disabled_raises_error(self, mock_settings, mock_get_transcript):
        """Test that fallback disabled raises ValueError."""
        from app.config import Settings
        
        # Mock settings with fallback disabled
        mock_settings.return_value = Settings(
            enable_audio_fallback=False,
            gcp_project_id=None,
            database_url="sqlite:///./test.db",
        )
        mock_get_transcript.side_effect = ValueError("No transcript available")
        
        with pytest.raises(ValueError, match="NO_TRANSCRIPT_AVAILABLE"):
            get_transcript_with_fallback("https://youtube.com/watch?v=test")

    @patch("app.services.transcript.get_youtube_transcript")
    @patch("app.services.transcript.download_youtube_audio")
    @patch("app.services.transcript.transcribe_audio_google")
    @patch("app.services.transcript.get_settings")
    @patch("tempfile.TemporaryDirectory")
    def test_audio_fallback_success(
        self,
        mock_tempdir,
        mock_settings,
        mock_transcribe,
        mock_download,
        mock_get_transcript,
    ):
        """Test successful audio fallback."""
        from app.config import Settings
        
        # Mock settings with fallback enabled
        mock_settings.return_value = Settings(
            enable_audio_fallback=True,
            gcp_project_id="test-project",
            gcp_location="us-central1",
            stt_language_code="en-US",
            stt_model=None,
            stt_max_audio_seconds=600,
            database_url="sqlite:///./test.db",
        )
        
        # Mock captions failure
        mock_get_transcript.side_effect = ValueError("No transcript available")
        
        # Mock temp directory
        temp_dir = Path("/tmp/test")
        temp_dir.mkdir(parents=True, exist_ok=True)
        mock_tempdir.return_value.__enter__.return_value = str(temp_dir)
        mock_tempdir.return_value.__exit__.return_value = None
        
        # Mock audio download
        audio_path = temp_dir / "test.mp3"
        audio_path.write_bytes(b"fake audio")
        mock_download.return_value = (temp_dir, audio_path)
        
        # Mock transcription
        mock_transcribe.return_value = "Transcribed text from audio"
        
        text, segments, source = get_transcript_with_fallback("https://youtube.com/watch?v=test")
        
        assert text == "Transcribed text from audio"
        assert segments is None
        assert source == "audio"
        
        # Verify mocks were called
        mock_download.assert_called_once()
        mock_transcribe.assert_called_once()

    @patch("app.services.transcript.get_youtube_transcript")
    @patch("app.services.transcript.download_youtube_audio")
    @patch("app.services.transcript.get_settings")
    def test_audio_fallback_missing_gcp_project(self, mock_settings, mock_download, mock_get_transcript):
        """Test that missing GCP project ID prevents fallback."""
        from app.config import Settings
        
        mock_settings.return_value = Settings(
            enable_audio_fallback=True,
            gcp_project_id=None,  # Missing project ID
            database_url="sqlite:///./test.db",
        )
        mock_get_transcript.side_effect = ValueError("No transcript available")
        
        with pytest.raises(ValueError, match="NO_TRANSCRIPT_AVAILABLE"):
            get_transcript_with_fallback("https://youtube.com/watch?v=test")
        
        # Should not attempt download
        mock_download.assert_not_called()

    @patch("app.services.transcript.get_youtube_transcript")
    @patch("app.services.transcript.download_youtube_audio")
    @patch("app.services.transcript.transcribe_audio_google")
    @patch("app.services.transcript.get_settings")
    @patch("tempfile.TemporaryDirectory")
    def test_audio_fallback_transcription_fails(
        self,
        mock_tempdir,
        mock_settings,
        mock_transcribe,
        mock_download,
        mock_get_transcript,
    ):
        """Test that transcription failure raises RuntimeError."""
        from app.config import Settings
        
        mock_settings.return_value = Settings(
            enable_audio_fallback=True,
            gcp_project_id="test-project",
            gcp_location="us-central1",
            stt_language_code="en-US",
            database_url="sqlite:///./test.db",
        )
        
        mock_get_transcript.side_effect = ValueError("No transcript available")
        
        temp_dir = Path("/tmp/test")
        temp_dir.mkdir(parents=True, exist_ok=True)
        mock_tempdir.return_value.__enter__.return_value = str(temp_dir)
        
        audio_path = temp_dir / "test.mp3"
        audio_path.write_bytes(b"fake audio")
        mock_download.return_value = (temp_dir, audio_path)
        
        # Mock transcription failure
        mock_transcribe.side_effect = RuntimeError("STT API error")
        
        with pytest.raises(RuntimeError, match="AUDIO_TRANSCRIPTION_FAILED"):
            get_transcript_with_fallback("https://youtube.com/watch?v=test")


@pytest.mark.audio_fallback
class TestAudioFallbackIntegration:
    """Integration tests for audio fallback (requires RUN_AUDIO_INTEGRATION=1)."""

    @pytest.mark.skipif(
        os.getenv("RUN_AUDIO_INTEGRATION") != "1",
        reason="Set RUN_AUDIO_INTEGRATION=1 to run integration tests",
    )
    def test_real_audio_fallback(self):
        """Test real audio fallback with a video that has no captions."""
        # This test requires:
        # - ENABLE_AUDIO_FALLBACK=1
        # - GCP_PROJECT_ID set
        # - Valid GCP credentials
        # - A YouTube video URL that has no captions
        
        # Skip if not configured
        if os.getenv("ENABLE_AUDIO_FALLBACK") != "1":
            pytest.skip("ENABLE_AUDIO_FALLBACK not set to 1")
        
        if not os.getenv("GCP_PROJECT_ID") and not os.getenv("VERTEX_PROJECT_ID"):
            pytest.skip("GCP_PROJECT_ID not set")
        
        # Use a test video URL (you may need to find one without captions)
        # For now, we'll skip this test as it requires real infrastructure
        pytest.skip("Requires real YouTube video without captions and GCP setup")

