"""
Tests for YouTube transcript service.
"""
from unittest.mock import MagicMock, patch

import pytest
from youtube_transcript_api import NoTranscriptFound

from app.services.youtube import extract_youtube_video_id, get_youtube_transcript


class TestVideoIDExtraction:
    """Test YouTube video ID extraction."""

    def test_extract_video_id_standard_url(self):
        """Test extracting ID from standard YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = extract_youtube_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_short_url(self):
        """Test extracting ID from short YouTube URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = extract_youtube_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_with_timestamp(self):
        """Test extracting ID from URL with timestamp."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s"
        video_id = extract_youtube_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid_url(self):
        """Test extracting ID from invalid URL."""
        url = "https://example.com/video"
        video_id = extract_youtube_video_id(url)
        assert video_id is None


class TestTranscriptFetching:
    """Test transcript fetching."""

    @patch("app.services.youtube.YouTubeTranscriptApi.get_transcript")
    def test_get_transcript_success(self, mock_get_transcript):
        """Test successful transcript fetch."""
        mock_transcript = [
            {"text": "Hello", "start": 0.0, "duration": 1.0},
            {"text": "world", "start": 1.0, "duration": 1.0},
        ]
        mock_get_transcript.return_value = mock_transcript

        text, segments = get_youtube_transcript("https://www.youtube.com/watch?v=test123")

        assert text == "Hello world"
        assert len(segments) == 2
        assert segments[0]["text"] == "Hello"

    @patch("app.services.youtube.YouTubeTranscriptApi.get_transcript")
    def test_get_transcript_no_transcript_found(self, mock_get_transcript):
        """Test handling when transcript is not available."""
        mock_get_transcript.side_effect = NoTranscriptFound("test123", None, None)

        # Should raise an error since fallback is disabled
        with pytest.raises(ValueError, match="No transcript available"):
            get_youtube_transcript("https://www.youtube.com/watch?v=test123")

    def test_get_transcript_invalid_url(self):
        """Test handling of invalid URL."""
        with pytest.raises(ValueError, match="Could not parse YouTube video id"):
            get_youtube_transcript("https://example.com/video")

