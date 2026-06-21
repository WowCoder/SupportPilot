"""
Base parser interface and ParsedPage data class.

All document parsers (Unstructured or custom) must implement
the BaseParser interface to produce ParsedPage objects.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ParsedPage:
    """Represents one page (or logical section) of a parsed document.

    Attributes:
        text: The extracted text content of the page.
        page: Page number (0-indexed, or section index for non-paginated formats).
        source: Source filename or identifier.
        metadata: Arbitrary metadata dict (e.g., headings, tables, layout info).
    """
    text: str
    page: int = 0
    source: str = ''
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    """Abstract base class for document parsers.

    All parsers must implement parse(file_path) → List[ParsedPage].
    """

    @abstractmethod
    def parse(self, file_path: str) -> List[ParsedPage]:
        """Parse a document file and return extracted pages."""
        raise NotImplementedError
