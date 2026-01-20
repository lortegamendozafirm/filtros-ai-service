"""Legal fundamentals loader for AI context."""

import os
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Cache for loaded fundamentals
_fundamentals_cache: Optional[str] = None


def load_fundamentals() -> str:
    """Load all legal fundamental documents from data/fundamentals directory.
    
    Returns:
        Concatenated text from all .md files in fundamentals directory
    """
    global _fundamentals_cache
    
    # Return cached version if available
    if _fundamentals_cache is not None:
        return _fundamentals_cache
    
    # Determine fundamentals directory path
    current_dir = Path(__file__).parent.parent
    fundamentals_dir = current_dir / "data"
    
    if not fundamentals_dir.exists():
        logger.warning(f"Fundamentals directory not found: {fundamentals_dir}")
        return ""
    
    fundamentals_text = ""
    md_files = list(fundamentals_dir.glob("*.md"))
    
    logger.info(f"Loading {len(md_files)} fundamental documents...")
    
    for md_file in sorted(md_files):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                fundamentals_text += f"\n\n--- {md_file.name} ---\n{content}"
                logger.debug(f"Loaded {md_file.name} ({len(content)} chars)")
        except Exception as e:
            logger.error(f"Error loading {md_file.name}: {e}")
    
    # Cache the result
    _fundamentals_cache = fundamentals_text
    logger.info(f"Loaded fundamentals: {len(fundamentals_text)} total characters")
    
    return fundamentals_text


def clear_fundamentals_cache() -> None:
    """Clear the fundamentals cache (useful for testing)."""
    global _fundamentals_cache
    _fundamentals_cache = None
