"""Text cleaning and normalization utilities."""

import re
from typing import Optional


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for file systems
    """
    # Remove invalid characters for Windows/Linux
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Replace multiple spaces with single underscore
    filename = re.sub(r'\s+', '_', filename)
    
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing underscores
    return filename.strip('_')


def clean_extracted_text(text: str) -> str:
    """Clean extracted PDF text.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common PDF artifacts
    text = re.sub(r'Page \d+ of \d+', '', text)
    
    # Normalize line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    return text.strip()


def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length in characters
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "... [TRUNCATED]"
