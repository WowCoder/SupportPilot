"""
Utility functions for SupportPilot
"""
import html
import re


def sanitize_input(text):
    """Sanitize user input to prevent XSS attacks"""
    if not text:
        return ''
    # Escape HTML special characters
    text = html.escape(text)
    # Remove any potential script tags (defense in depth)
    text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Limit length
    if len(text) > 10000:
        text = text[:10000]
    return text.strip()
