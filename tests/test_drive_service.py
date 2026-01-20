"""Tests for drive service."""

import pytest
from app.services.drive_service import extract_id_from_url
from app.utils.text_cleaner import sanitize_filename


class TestExtractIdFromUrl:
    """Test URL ID extraction."""
    
    def test_extract_id_format_1(self):
        """Test /d/ID format."""
        url = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/view"
        file_id = extract_id_from_url(url)
        assert file_id == "1AbCdEfGhIjKlMnOpQrStUvWxYz"
    
    def test_extract_id_format_2(self):
        """Test id=ID format."""
        url = "https://drive.google.com/open?id=1AbCdEfGhIjKlMnOpQrStUvWxYz"
        file_id = extract_id_from_url(url)
        assert file_id == "1AbCdEfGhIjKlMnOpQrStUvWxYz"
    
    def test_extract_id_format_3(self):
        """Test open?id=ID format."""
        url = "https://docs.google.com/document/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/edit"
        file_id = extract_id_from_url(url)
        assert file_id == "1AbCdEfGhIjKlMnOpQrStUvWxYz"
    
    def test_extract_id_invalid_url(self):
        """Test invalid URL."""
        url = "https://example.com/not-a-drive-url"
        file_id = extract_id_from_url(url)
        assert file_id is None


class TestSanitizeFilename:
    """Test filename sanitization."""
    
    def test_remove_invalid_chars(self):
        """Test removal of invalid characters."""
        filename = 'test<>:"/\\|?*.txt'
        result = sanitize_filename(filename)
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
    
    def test_replace_spaces(self):
        """Test space replacement."""
        filename = "test   multiple   spaces.txt"
        result = sanitize_filename(filename)
        assert "   " not in result
        assert "_" in result
    
    def test_remove_leading_trailing_underscores(self):
        """Test underscore trimming."""
        filename = "___test___"
        result = sanitize_filename(filename)
        assert not result.startswith("_")
        assert not result.endswith("_")
