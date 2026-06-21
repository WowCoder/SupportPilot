"""Quality scoring stage for RAG offline pipeline.

Scores text chunks on 5 dimensions (0-100 total) and filters low-quality
chunks below a configurable threshold.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, List

logger = logging.getLogger(__name__)


@dataclass
class QualityConfig:
    """Configuration for quality stage."""

    enabled: bool = True
    min_score: int = 60


class QualityStage:
    """Quality scoring stage that filters chunks below a quality threshold.

    Scores each chunk on 5 dimensions (20 pts each):
    - Length score
    - Sentence completeness (punctuation)
    - Information density
    - Noise ratio (inverse)
    - Language coherence
    """

    def __init__(self, config: Any) -> None:
        self.config = config

    def __call__(self, chunks: List[Any]) -> List[Any]:
        """Filter chunks, keeping only those above min_score.

        Args:
            chunks: List of document-like objects with ``page_content``.

        Returns:
            Filtered list of chunks.
        """
        if not self.config.enabled:
            return chunks
        return [c for c in chunks if self.score_text(c.page_content) >= self.config.min_score]

    @staticmethod
    def score_text(text: str) -> int:
        """Score text quality 0-100.

        Logic from pipeline.py ``_quality_score``.

        Args:
            text: Text to score.

        Returns:
            Quality score (0-100).
        """
        if not text or not text.strip():
            return 0

        score = 0
        text_len = len(text.strip())

        # Length score (20 points)
        if 100 <= text_len <= 2000:
            score += 20
        elif 50 <= text_len < 100 or 2000 < text_len <= 3000:
            score += 10

        # Sentence completeness (20 points)
        has_punctuation = bool(re.search(r'[,.!?!.:;?]', text))
        if has_punctuation:
            score += 20

        # Information density (20 points)
        # Count meaningful characters (not just numbers/symbols)
        meaningful = len(re.findall(r'[一-龥a-zA-Z]', text))
        if text_len > 0 and meaningful / text_len > 0.3:
            score += 20

        # Noise ratio (20 points)
        noise_pattern = r'^[\d\s\.\-\(\)]+$'
        noise_lines = [line for line in text.split('\n') if re.match(noise_pattern, line.strip())]
        if len(noise_lines) / max(len(text.split('\n')), 1) < 0.2:
            score += 20

        # Language detection (20 points) - simplified check
        # Chinese or English characters should dominate
        if meaningful > text_len * 0.5:
            score += 20

        return score
