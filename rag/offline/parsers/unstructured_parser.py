"""
Unstructured-based document parser.

Wraps the `unstructured` library to provide a unified parsing interface
for PDF, DOCX, TXT, HTML, Markdown, and other document formats.
"""
import logging
import os
from typing import List

from rag.offline.parsers.base import BaseParser, ParsedPage
from rag.offline.pipeline_config import ParsingConfig

logger = logging.getLogger(__name__)


class UnstructuredParser(BaseParser):
    """Document parser powered by Unstructured.io.

    Supports: PDF, DOCX, TXT, HTML, MD, and more.
    Automatically detects layout, extracts tables, and handles
    multi-column documents.

    Usage:
        parser = UnstructuredParser(ParsingConfig(strategy='auto'))
        pages = parser.parse('/path/to/document.pdf')
    """

    def __init__(self, config: ParsingConfig = None):
        self.config = config or ParsingConfig()

    def parse(self, file_path: str) -> List[ParsedPage]:
        """Parse a document into a list of ParsedPage objects.

        Uses Unstructured's auto-detection to pick the best partitioning
        strategy based on file type and content.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        # Route to appropriate method based on file type
        if ext == '.txt':
            return self._parse_text(file_path)

        # For PDF, DOCX, and other formats, use unstructured.partition
        try:
            elements = self._partition(file_path)
            return self._elements_to_pages(elements, file_path)
        except Exception as e:
            logger.error("Unstructured parsing failed for %s: %s", file_path, e)
            raise

    def _partition(self, file_path: str):
        """Call unstructured.partition with appropriate settings."""
        from unstructured.partition.auto import partition

        strategy = self.config.strategy
        if strategy == 'auto':
            # Let unstructured decide based on file type
            return partition(
                filename=file_path,
                languages=self.config.languages,
                strategy='auto',
            )

        return partition(
            filename=file_path,
            languages=self.config.languages,
            strategy=strategy,
        )

    def _elements_to_pages(self, elements, source: str) -> List[ParsedPage]:
        """Convert unstructured elements to ParsedPage objects.

        Groups elements by page number. File formats without page
        boundaries (TXT, MD) are treated as a single page.
        """
        # Group elements by detected page number
        pages_map = {}

        for el in elements:
            page_num = getattr(el.metadata, 'page_number', 0) if el.metadata else 0
            page_num = page_num or 0  # default to page 0 if None

            text = str(el) if el.text else ''
            if not text.strip():
                continue

            if page_num not in pages_map:
                pages_map[page_num] = []
            pages_map[page_num].append(text)

        if not pages_map:
            logger.warning("No text content extracted from %s", source)
            return []

        # Build ParsedPage objects sorted by page number
        pages = []
        for page_num in sorted(pages_map.keys()):
            lines = pages_map[page_num]
            text = '\n'.join(lines)
            pages.append(ParsedPage(
                text=text,
                page=page_num,
                source=os.path.basename(source),
                metadata={'filepath': source},
            ))

        return pages

    def _parse_text(self, file_path: str) -> List[ParsedPage]:
        """Parse plain text files with encoding detection.

        TXT files don't benefit from Unstructured's layout analysis,
        so we handle them directly with multi-encoding support.
        """
        content = None
        for encoding in (self.config.encoding,) + self.config.fallback_encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            raise ValueError(
                f"Failed to decode {file_path} with encodings: "
                f"{(self.config.encoding,) + self.config.fallback_encodings}"
            )

        if not content.strip():
            logger.warning("Empty file: %s", file_path)
            return []

        return [ParsedPage(
            text=content,
            page=0,
            source=os.path.basename(file_path),
            metadata={'filepath': file_path, 'encoding': encoding},
        )]


def get_parser(file_path: str, config: ParsingConfig = None) -> BaseParser:
    """Factory: return a parser suitable for the given file.

    Currently always returns UnstructuredParser since it handles
    all supported formats.
    """
    ext = os.path.splitext(file_path)[1].lower()
    supported = {'.pdf', '.docx', '.txt', '.html', '.htm', '.md', '.rst', '.xml'}
    if ext not in supported:
        raise ValueError(
            f"Unsupported file extension: {ext}. "
            f"Supported: {', '.join(sorted(supported))}"
        )
    return UnstructuredParser(config)
