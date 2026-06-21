"""Cleaning stage for RAG offline pipeline.

Merges cleaning logic from two sources:

- pipeline.py ``RAGUtils``: repeated line detection across pages
  (``_detect_repeated_lines``), header/footer removal (``_remove_headers_footers``),
  short noise-line filtering (``_clean_text``).

- cleaning.py ``DocumentCleaner``: OCR corrections (``OCR_CORRECTIONS``),
  noise patterns (``NOISE_PATTERNS``), page number patterns
  (``PAGE_NUMBER_PATTERNS``), OCR post-processing, whitespace normalization.

Also preserves the ``DocumentCleaner`` / ``CleaningOptions`` / ``ExtractResult`` /
``CleaningResult`` API for the interactive cleaning preview UI in
``app/api/routes.py``.
"""

import logging
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from rag.offline.parsers.base import ParsedPage
from rag.offline.pipeline_config import CleaningConfig

logger = logging.getLogger(__name__)


# ======================================================================
# CleaningStage — pipeline stage (operates on ParsedPage objects)
# ======================================================================

class CleaningStage:
    """Document cleaning stage for the RAG offline ETL pipeline.

    Two-phase design:

    1. **Page-level detection** -- ``_detect_repeated_lines`` scans every page
       to build a set of lines that appear on more than *threshold* fraction
       of all pages (identifying running headers / footers).

    2. **Per-page cleaning pipeline** -- each page passes through an ordered
       sequence of filters controlled by ``CleaningConfig`` booleans:

       * remove headers/footers  (``repeated_lines`` set)
       * remove page numbers     (``PAGE_NUMBER_PATTERNS``)
       * OCR post-processing     (``OCR_CORRECTIONS``)
       * remove noise lines      (``NOISE_PATTERNS``)
       * normalize whitespace    (multiple spaces, trailing space, blank lines)

    Pages that become empty after cleaning are dropped from the result.
    """

    # Common OCR error patterns (l <-> 1, O <-> 0, etc.)
    # From cleaning.py DocumentCleaner.OCR_CORRECTIONS
    OCR_CORRECTIONS = {
        # English OCR errors
        r'\bl\b': '1',                     # standlone 'l' -> '1'
        r'\bO\b': '0',                     # standlone 'O' -> '0'
        r'(?<=[0-9])l(?=[0-9])': '1',     # l between digits -> 1
        r'(?<=[0-9])O(?=[0-9])': '0',     # O between digits -> 0
        r'rn': 'm',                        # rn -> m (common OCR merge error)
        r'cl\.': '1.',                     # cl. -> 1.
        r'(?<=\d)\.(?=\d)': '.',          # ensure decimal points stay
        # Chinese OCR errors
        r'口口': '',                        # box placeholders
        r'□□': '',                          # square placeholders
        r'◆◆': '',                          # diamond placeholders
        r'[\x00-\x08\x0b\x0c\x0e-\x1f]': '',  # control chars
    }

    # Noise lines to remove entirely
    # From cleaning.py DocumentCleaner.NOISE_PATTERNS
    NOISE_PATTERNS = [
        r'^\s*\.{3,}\s*$',                # lines with only dots
        r'^\s*[-=~]{3,}\s*$',             # lines with only dashes/equals
        r'^\s*[\*\#]{3,}\s*$',            # lines with only stars/hash
        r'^\s*_+$\s*$',                    # lines with only underscores
        r'^\[\s*\]$',                      # empty brackets
        r'^\(\s*\)$',                      # empty parentheses
    ]

    # Page number line patterns
    # From cleaning.py DocumentCleaner.PAGE_NUMBER_PATTERNS
    PAGE_NUMBER_PATTERNS = [
        r'^第\s*\d+\s*页\s*$',             # Chinese: 第 1 页
        r'^\s*[-=]+\s*\d+\s*[-=]+\s*$',   # - 1 -  or = 1 =
        r'^\s*Page\s*\d+\s*$',             # English: Page 1
        r'^\s*p\.\s*\d+\s*$',              # p. 1
        r'^\s*\d+\s*/\s*\d+\s*$',          # 1/10
        r'^\s*-\s*\d+\s*-$',               # - 1 -
    ]

    def __init__(self, config: CleaningConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def __call__(self, pages: List[ParsedPage]) -> List[ParsedPage]:
        """Clean all pages through the multi-stage cleaning pipeline.

        Order of operations:

        1. **Detect repeated lines** across all pages (identifies running
           headers and footers).
        2. **Per-page pipeline** (each step is gated by its corresponding
           ``CleaningConfig`` boolean):

           * Remove headers/footers matching the repeated-lines set.
           * Remove page-number lines (``PAGE_NUMBER_PATTERNS``).
           * Apply OCR post-processing corrections (``OCR_CORRECTIONS``).
           * Remove noise-only lines (``NOISE_PATTERNS``).
           * Normalize whitespace (collapse spaces, trim trailing,
             condense blank lines).
        3. **Drop empty pages** -- any page whose text is blank after
           cleaning is excluded from the result.

        Args:
            pages: Parsed pages from the parsing stage.

        Returns:
            Cleaned pages with empty pages filtered out.
        """
        # Phase 1: detect repeated lines across all pages
        repeated_lines = self._detect_repeated_lines(
            pages, threshold=self.config.repeated_line_threshold,
        )

        # Phase 2: per-page cleaning pipeline
        cleaned: List[ParsedPage] = []
        for page in pages:
            text = page.text

            if self.config.remove_headers_footers:
                text = self._remove_headers_footers(text, repeated_lines)
            if self.config.remove_page_numbers:
                text = self._remove_page_numbers(text)
            if self.config.ocr_postprocess:
                text = self._ocr_postprocess(text)
            if self.config.clean_noise_chars:
                text = self._clean_noise_lines(text)
            if self.config.normalize_whitespace:
                text = self._normalize_whitespace(text)

            if text.strip():
                cleaned.append(ParsedPage(
                    text=text,
                    page=page.page,
                    source=page.source,
                    metadata=page.metadata,
                ))

        removed = len(pages) - len(cleaned)
        if removed:
            logger.info(
                'Cleaning complete: %d pages in, %d pages out (%d empty pages dropped)',
                len(pages), len(cleaned), removed,
            )
        else:
            logger.info(
                'Cleaning complete: %d pages in, %d pages out',
                len(pages), len(cleaned),
            )
        return cleaned

    # ------------------------------------------------------------------
    # Phase 1 -- page-level detection
    # ------------------------------------------------------------------

    def _detect_repeated_lines(
        self, pages: List[ParsedPage], threshold: float = 0.5,
    ) -> Set[str]:
        """Detect header / footer lines that appear on multiple pages.

        Merged from:
        * pipeline.py ``RAGUtils._detect_repeated_lines``
        * cleaning.py ``DocumentCleaner._detect_repeated_lines``

        A line is considered "repeated" when it appears on at least
        ``max(len(pages) * threshold, 2)`` distinct pages.  Lines longer
        than 100 chars are excluded (they are unlikely to be headers or
        footers).  Lines shorter than ``config.min_line_length`` are also
        excluded as probable noise.

        Args:
            pages: Parsed pages.
            threshold: Minimum fraction of pages a line must appear on
                to be considered repeated (default 0.5).

        Returns:
            Set of repeated lines to filter.
        """
        if not pages:
            return set()

        min_page_count = max(int(len(pages) * threshold), 2)

        line_counts: Counter = Counter()
        for page in pages:
            lines = set(page.text.strip().split('\n'))
            for line in lines:
                stripped = line.strip()
                if stripped and len(stripped) < 100:
                    line_counts[stripped] += 1

        repeated = {
            line
            for line, count in line_counts.items()
            if count >= min_page_count
        }

        if repeated:
            logger.info(
                'Detected %d repeated line(s) as headers/footers (threshold=%.2f, min_pages=%d)',
                len(repeated), threshold, min_page_count,
            )
        return repeated

    # ------------------------------------------------------------------
    # Phase 2 -- per-page cleaning methods
    # ------------------------------------------------------------------

    def _remove_headers_footers(self, text: str, repeated_lines: Set[str]) -> str:
        """Remove header / footer lines from a page.

        From pipeline.py ``RAGUtils._remove_headers_footers``.  Page-number
        removal is handled separately by ``_remove_page_numbers``.

        Args:
            text: Page text.
            repeated_lines: Set of lines identified as running headers
                or footers.

        Returns:
            Text with header/footer lines removed.
        """
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            if line.strip() in repeated_lines:
                continue
            cleaned.append(line)
        return '\n'.join(cleaned)

    def _remove_page_numbers(self, text: str) -> str:
        """Remove lines that match known page-number patterns.

        From cleaning.py ``DocumentCleaner._remove_page_numbers`` using
        ``PAGE_NUMBER_PATTERNS``.

        Args:
            text: Page text.

        Returns:
            Text with page-number lines removed.
        """
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if any(re.match(p, stripped, re.IGNORECASE) for p in self.PAGE_NUMBER_PATTERNS):
                continue
            cleaned.append(line)
        return '\n'.join(cleaned)

    def _ocr_postprocess(self, text: str) -> str:
        """Apply OCR error corrections.

        From cleaning.py ``DocumentCleaner._ocr_postprocess`` using
        ``OCR_CORRECTIONS``.

        Applies every pattern in ``OCR_CORRECTIONS`` as a ``re.sub``
        replacement over the entire page text.

        Args:
            text: Page text.

        Returns:
            Text with common OCR errors corrected.
        """
        for pattern, replacement in self.OCR_CORRECTIONS.items():
            text = re.sub(pattern, replacement, text)
        return text

    def _clean_noise_lines(self, text: str) -> str:
        """Remove lines that consist only of noise characters.

        From cleaning.py ``DocumentCleaner._clean_noise_chars`` using
        ``NOISE_PATTERNS``.

        Each pattern in ``NOISE_PATTERNS`` is matched with
        ``re.MULTILINE`` so it matches whole lines.  Matching lines are
        replaced with the empty string (removed).

        Args:
            text: Page text.

        Returns:
            Text with noise-only lines removed.
        """
        for pattern in self.NOISE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text.

        From cleaning.py ``DocumentCleaner._normalize_whitespace``.

        Operations:

        1. Collapse runs of horizontal whitespace (spaces / tabs) into a
           single space.
        2. Strip trailing whitespace from every line.
        3. Collapse three or more consecutive blank lines into two.

        Args:
            text: Page text.

        Returns:
            Text with normalized whitespace.
        """
        # Collapse multiple spaces/tabs into a single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Remove trailing whitespace from every line
        lines = text.split('\n')
        text = '\n'.join(line.rstrip() for line in lines)
        # Collapse 3+ blank lines into 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text


# ======================================================================
# Interactive cleaning API (used by app/api/routes.py)
# ======================================================================

@dataclass
class CleaningOptions:
    """Options for interactive document cleaning preview.

    Mirrors the original ``rag.offline.cleaning.CleaningOptions`` dataclass.
    """
    remove_headers_footers: bool = True
    remove_page_numbers: bool = True
    clean_noise_chars: bool = True
    normalize_whitespace: bool = True
    ocr_postprocess: bool = True
    filter_non_content: bool = True


@dataclass
class CleaningResult:
    """Result of interactive document cleaning."""
    original_text: str
    cleaned_text: str
    removed_lines: List[str] = field(default_factory=list)
    removed_chars_count: int = 0
    reduction_percent: float = 0.0
    cleaning_stats: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractResult:
    """Result of raw text extraction (interactive preview flow)."""
    text: str
    pages: List[Dict[str, Any]] = field(default_factory=list)
    pdf_metadata: Dict[str, Any] = field(default_factory=dict)
    file_type: str = ""
    total_chars: int = 0
    total_lines: int = 0


class DocumentCleaner:
    """Interactive document cleaner used by the cleaning preview UI.

    Handles raw text extraction (pdfplumber, docx2txt) and the interactive
    cleaning preview / confirm workflow.  This is **not** the same as
    ``CleaningStage``, which is a callable pipeline stage operating on
    ``ParsedPage`` objects.

    References ``CleaningStage`` class constants for OCR / noise / page-number
    patterns to avoid duplication.
    """

    # Page number patterns (shared with CleaningStage, which is defined above)
    PAGE_NUMBER_PATTERNS = CleaningStage.PAGE_NUMBER_PATTERNS

    def __init__(self):
        self._temp_files = []

    def extract_raw(self, file_path: str) -> ExtractResult:
        """Extract raw text and PDF metadata from document.

        Args:
            file_path: Path to the document file.

        Returns:
            ExtractResult with raw text, pages, and metadata.
        """
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == '.pdf':
                return self._extract_pdf_raw(file_path)
            elif ext == '.txt':
                return self._extract_txt_raw(file_path)
            elif ext == '.docx':
                return self._extract_docx_raw(file_path)
            else:
                logger.warning(f'Unsupported file type: {ext}')
                return ExtractResult(text="", file_type=ext)

        except Exception as e:
            logger.error(f'Error extracting raw text from {file_path}: {e}', exc_info=True)
            raise

    def _extract_pdf_raw(self, file_path: str) -> ExtractResult:
        """Extract raw text from PDF using pdfplumber."""
        import pdfplumber

        pages = []
        pdf_metadata = {}

        try:
            with pdfplumber.open(file_path) as pdf:
                if pdf.metadata:
                    pdf_metadata = {
                        'title': pdf.metadata.get('Title', ''),
                        'author': pdf.metadata.get('Author', ''),
                        'subject': pdf.metadata.get('Subject', ''),
                        'creator': pdf.metadata.get('Creator', ''),
                        'producer': pdf.metadata.get('Producer', ''),
                        'creation_date': pdf.metadata.get('CreationDate', ''),
                        'modified_date': pdf.metadata.get('ModDate', ''),
                        'page_count': len(pdf.pages),
                    }

                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""
                    pages.append({
                        'text': page_text,
                        'page': page_num,
                        'chars': len(page_text),
                        'lines': len(page_text.split('\n')),
                    })

            full_text = '\n\n'.join(p['text'] for p in pages)

            return ExtractResult(
                text=full_text,
                pages=pages,
                pdf_metadata=pdf_metadata,
                file_type='pdf',
                total_chars=len(full_text),
                total_lines=len(full_text.split('\n')),
            )

        except Exception as e:
            logger.error(f'Error extracting PDF: {e}', exc_info=True)
            raise

    def _extract_txt_raw(self, file_path: str) -> ExtractResult:
        """Extract raw text from TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            sections = text.split('\f') if '\f' in text else [text]
            pages = []
            for i, section in enumerate(sections, 1):
                pages.append({
                    'text': section,
                    'page': i,
                    'chars': len(section),
                    'lines': len(section.split('\n')),
                })

            return ExtractResult(
                text=text,
                pages=pages,
                pdf_metadata={},
                file_type='txt',
                total_chars=len(text),
                total_lines=len(text.split('\n')),
            )

        except UnicodeDecodeError:
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Unable to decode text file")

            pages = [{
                'text': text,
                'page': 1,
                'chars': len(text),
                'lines': len(text.split('\n')),
            }]
            return ExtractResult(
                text=text,
                pages=pages,
                pdf_metadata={},
                file_type='txt',
                total_chars=len(text),
                total_lines=len(text.split('\n')),
            )

    def _extract_docx_raw(self, file_path: str) -> ExtractResult:
        """Extract raw text from DOCX file."""
        from docx2txt import docx2txt

        text = docx2txt.process(file_path)
        pages = [{
            'text': text,
            'page': 1,
            'chars': len(text),
            'lines': len(text.split('\n')),
        }]
        return ExtractResult(
            text=text,
            pages=pages,
            pdf_metadata={},
            file_type='docx',
            total_chars=len(text),
            total_lines=len(text.split('\n')),
        )

    def clean(self, raw_data: ExtractResult, options: CleaningOptions = None) -> CleaningResult:
        """Execute cleaning on extracted raw data (interactive preview flow).

        Args:
            raw_data: ExtractResult from extract_raw().
            options: CleaningOptions to control cleaning behavior.

        Returns:
            CleaningResult with cleaned text and statistics.
        """
        if options is None:
            options = CleaningOptions()

        original_text = raw_data.text
        cleaned_text = original_text
        removed_lines = []
        cleaning_stats = {
            'headers_footers_removed': 0,
            'page_numbers_removed': 0,
            'noise_chars_removed': 0,
            'whitespace_normalized': 0,
            'ocr_corrections': 0,
        }

        # Step 1: Detect and remove headers/footers
        if options.remove_headers_footers and raw_data.pages:
            repeated_lines = self._detect_repeated_lines(raw_data.pages)
            cleaned_text, removed = self._remove_repeated_lines(cleaned_text, repeated_lines)
            removed_lines.extend(removed)
            cleaning_stats['headers_footers_removed'] = len(removed)

        # Step 2: Remove page numbers
        if options.remove_page_numbers:
            cleaned_text, removed = self._remove_page_numbers(cleaned_text)
            removed_lines.extend(removed)
            cleaning_stats['page_numbers_removed'] = len(removed)

        # Step 3: Clean noise characters
        if options.clean_noise_chars:
            cleaned_text, count = self._clean_noise_chars(cleaned_text)
            cleaning_stats['noise_chars_removed'] = count

        # Step 4: OCR post-processing
        if options.ocr_postprocess:
            cleaned_text, count = self._ocr_postprocess(cleaned_text)
            cleaning_stats['ocr_corrections'] = count

        # Step 5: Normalize whitespace
        if options.normalize_whitespace:
            cleaned_text, count = self._normalize_whitespace(cleaned_text)
            cleaning_stats['whitespace_normalized'] = count

        # Step 6: Filter non-content
        if options.filter_non_content:
            cleaned_text, removed = self._filter_non_content(cleaned_text)
            removed_lines.extend(removed)

        original_chars = len(original_text)
        cleaned_chars = len(cleaned_text)
        removed_chars_count = original_chars - cleaned_chars
        reduction_percent = (removed_chars_count / original_chars * 100) if original_chars > 0 else 0

        metadata = self._extract_metadata(raw_data, cleaned_text)

        return CleaningResult(
            original_text=original_text,
            cleaned_text=cleaned_text,
            removed_lines=removed_lines,
            removed_chars_count=removed_chars_count,
            reduction_percent=round(reduction_percent, 2),
            cleaning_stats=cleaning_stats,
            metadata=metadata,
        )

    def preview(self, raw_data: ExtractResult, options: CleaningOptions = None) -> Dict[str, Any]:
        """Preview cleaning effect with before/after comparison.

        Args:
            raw_data: ExtractResult from extract_raw().
            options: CleaningOptions to control cleaning behavior.

        Returns:
            Dict with preview data for visualization.
        """
        result = self.clean(raw_data, options)

        original_lines = result.original_text.split('\n')
        cleaned_lines = result.cleaned_text.split('\n')
        deleted_line_set = set(result.removed_lines)

        diff_result = []
        original_idx = 0
        cleaned_idx = 0

        while original_idx < len(original_lines) or cleaned_idx < len(cleaned_lines):
            orig_line = original_lines[original_idx] if original_idx < len(original_lines) else None
            clean_line = cleaned_lines[cleaned_idx] if cleaned_idx < len(cleaned_lines) else None

            if orig_line and orig_line.strip() in deleted_line_set:
                diff_result.append({
                    'type': 'removed',
                    'original': orig_line,
                    'cleaned': None,
                    'original_line_num': original_idx + 1,
                })
                original_idx += 1
            elif orig_line == clean_line:
                diff_result.append({
                    'type': 'unchanged',
                    'original': orig_line,
                    'cleaned': clean_line,
                    'original_line_num': original_idx + 1,
                    'cleaned_line_num': cleaned_idx + 1,
                })
                original_idx += 1
                cleaned_idx += 1
            elif clean_line and orig_line and clean_line != orig_line:
                diff_result.append({
                    'type': 'modified',
                    'original': orig_line,
                    'cleaned': clean_line,
                    'original_line_num': original_idx + 1,
                    'cleaned_line_num': cleaned_idx + 1,
                })
                original_idx += 1
                cleaned_idx += 1
            elif clean_line and not orig_line:
                diff_result.append({
                    'type': 'added',
                    'original': None,
                    'cleaned': clean_line,
                    'cleaned_line_num': cleaned_idx + 1,
                })
                cleaned_idx += 1
            else:
                if original_idx < len(original_lines):
                    original_idx += 1
                if cleaned_idx < len(cleaned_lines):
                    cleaned_idx += 1

        return {
            'success': True,
            'original_text': result.original_text,
            'cleaned_text': result.cleaned_text,
            'original_chars': len(result.original_text),
            'cleaned_chars': len(result.cleaned_text),
            'removed_chars_count': result.removed_chars_count,
            'reduction_percent': result.reduction_percent,
            'cleaning_stats': result.cleaning_stats,
            'metadata': result.metadata,
            'diff': diff_result[:500],
            'total_diff_lines': len(diff_result),
        }

    # ------------------------------------------------------------------
    # Internal cleaning methods (mirror the old DocumentCleaner logic)
    # ------------------------------------------------------------------

    def _detect_repeated_lines(self, pages: List[Dict], threshold: float = 0.5) -> Set[str]:
        """Detect header/footer lines that appear in multiple pages."""
        if not pages:
            return set()

        line_counts = Counter()
        for page_data in pages:
            lines = set(page_data['text'].strip().split('\n'))
            for line in lines:
                stripped = line.strip()
                if stripped and len(stripped) < 100:
                    line_counts[stripped] += 1

        min_count = int(len(pages) * threshold)
        repeated = {
            line for line, count in line_counts.items()
            if count >= max(min_count, 2) and len(line) < 100
        }

        logger.info(f'Detected {len(repeated)} repeated lines (headers/footers)')
        return repeated

    @staticmethod
    def _remove_repeated_lines(text: str, repeated_lines: Set[str]):
        lines = text.split('\n')
        cleaned = []
        removed = []
        for line in lines:
            stripped = line.strip()
            if stripped in repeated_lines:
                removed.append(stripped)
                continue
            cleaned.append(line)
        return '\n'.join(cleaned), removed

    def _remove_page_numbers(self, text: str):
        lines = text.split('\n')
        cleaned = []
        removed = []
        for line in lines:
            stripped = line.strip()
            is_page_num = any(
                re.match(p, stripped, re.IGNORECASE)
                for p in self.PAGE_NUMBER_PATTERNS
            )
            if is_page_num:
                removed.append(stripped)
            else:
                cleaned.append(line)
        return '\n'.join(cleaned), removed

    def _clean_noise_chars(self, text: str):
        count = 0
        cleaned = text
        for pattern in CleaningStage.NOISE_PATTERNS:
            matches = re.findall(pattern, cleaned, re.MULTILINE)
            count += len(matches)
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
        return cleaned, count

    def _ocr_postprocess(self, text: str):
        count = 0
        cleaned = text
        for pattern, replacement in CleaningStage.OCR_CORRECTIONS.items():
            matches = re.findall(pattern, cleaned)
            if matches:
                count += len(matches)
                cleaned = re.sub(pattern, replacement, cleaned)
        return cleaned, count

    @staticmethod
    def _normalize_whitespace(text: str):
        count = 0
        original_len = len(text)
        cleaned = re.sub(r'[ \t]+', ' ', text)
        lines = cleaned.split('\n')
        lines = [line.rstrip() for line in lines]
        cleaned = '\n'.join(lines)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        count = original_len - len(cleaned)
        return cleaned, count

    @staticmethod
    def _filter_non_content(text: str):
        lines = text.split('\n')
        cleaned = []
        removed = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if cleaned and cleaned[-1].strip():
                    cleaned.append(line)
                continue
            if len(stripped) < 3 and re.match(r'^[\d\.\s\-\*]+$', stripped):
                removed.append(stripped)
                continue
            if re.match(r'^\.\.\.\.\.*$', stripped):
                removed.append(stripped)
                continue
            cleaned.append(line)
        return '\n'.join(cleaned), removed

    @staticmethod
    def _extract_metadata(raw_data: ExtractResult, cleaned_text: str) -> Dict[str, Any]:
        metadata = {
            'title': '',
            'author': '',
            'date': '',
            'category': '',
            'source': '',
            'page_count': 0,
        }
        if raw_data.pdf_metadata:
            metadata['title'] = raw_data.pdf_metadata.get('title', '')
            metadata['author'] = raw_data.pdf_metadata.get('author', '')
            metadata['page_count'] = raw_data.pdf_metadata.get('page_count', 0)

            creation_date = raw_data.pdf_metadata.get('creation_date', '')
            if creation_date:
                try:
                    if creation_date.startswith('D:'):
                        date_str = creation_date[2:10]
                        metadata['date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                except Exception:
                    pass

        if not metadata['title']:
            lines = cleaned_text.strip().split('\n')
            for line in lines[:10]:
                stripped = line.strip()
                if len(stripped) > 10 and len(stripped) < 100:
                    metadata['title'] = stripped
                    break

        return metadata


# Global singleton for the interactive cleaning preview API
document_cleaner = DocumentCleaner()
