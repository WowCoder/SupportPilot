"""
Utility functions for SupportPilot
"""
import html
import re
from typing import Optional


def sanitize_input(text: Optional[str]) -> str:
    """
    Sanitize user input to prevent XSS attacks

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized text with HTML escaped and length limited
    """
    if not text:
        return ''

    # Escape HTML special characters
    text = html.escape(text)

    # Remove any potential script tags (defense in depth)
    text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Limit length to prevent DoS
    if len(text) > 10000:
        text = text[:10000]

    return text.strip()
