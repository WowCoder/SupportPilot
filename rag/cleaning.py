"""
Document Cleaning Module for SupportPilot

Provides data cleaning and metadata extraction for documents before chunking.
Supports visualization of cleaning effects with before/after comparison.
"""
import pdfplumber
import os
import re
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


@dataclass
class CleaningOptions:
    """Options for document cleaning"""
    remove_headers_footers: bool = True
    remove_page_numbers: bool = True
    clean_noise_chars: bool = True
    normalize_whitespace: bool = True
    ocr_postprocess: bool = True
    filter_non_content: bool = True


@dataclass
class CleaningResult:
    """Result of document cleaning"""
    original_text: str
    cleaned_text: str
    removed_lines: List[str] = field(default_factory=list)
    removed_chars_count: int = 0
    reduction_percent: float = 0.0
    cleaning_stats: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractResult:
    """Result of raw text extraction"""
    text: str
    pages: List[Dict[str, Any]] = field(default_factory=list)
    pdf_metadata: Dict[str, Any] = field(default_factory=dict)
    file_type: str = ""
    total_chars: int = 0
    total_lines: int = 0


class DocumentCleaner:
    """Document cleaning and metadata extraction"""

    # Common OCR error patterns (l↔1, O↔0, etc.)
    OCR_CORRECTIONS = {
        # English OCR errors
        r'\bl\b': '1',  # standalone 'l' -> '1'
        r'\bO\b': '0',  # standalone 'O' -> '0'
        r'(?<=[0-9])l(?=[0-9])': '1',  # l between digits -> 1
        r'(?<=[0-9])O(?=[0-9])': '0',  # O between digits -> 0
        r'rn': 'm',  # rn -> m (common OCR merge error)
        r'cl\.': '1.',  # cl. -> 1.
        r'(?<=\d)\.(?=\d)': '.',  # Ensure decimal points stay

        # Chinese OCR errors
        r'口口': '',  # Box placeholders
        r'□□': '',  # Square placeholders
        r'◆◆': '',  # Diamond placeholders
        r'[\u0000-\u0008\u000b\u000c\u000e-\u001f]': '',  # Control chars
    }

    # Noise patterns to clean
    NOISE_PATTERNS = [
        r'^\s*\.{3,}\s*$',  # Lines with only dots
        r'^\s*[-=~]{3,}\s*$',  # Lines with only dashes/equals
        r'^\s*[\*\#]{3,}\s*$',  # Lines with only stars/hash
        r'^\s*_+$\s*$',  # Lines with only underscores
        r'^\[\s*\]$',  # Empty brackets
        r'^\(\s*\)$',  # Empty parentheses
    ]

    # Page number patterns
    PAGE_NUMBER_PATTERNS = [
        r'^第\s*\d+\s*页\s*$',  # Chinese: 第 1 页
        r'^\s*[-=]+\s*\d+\s*[-=]+\s*$',  # - 1 - or = 1 =
        r'^\s*Page\s*\d+\s*$',  # English: Page 1
        r'^\s*p\.\s*\d+\s*$',  # p. 1
        r'^\s*\d+\s*/\s*\d+\s*$',  # 1/10
        r'^\s*-\s*\d+\s*-$',  # - 1 -
    ]

    def __init__(self):
        self._temp_files = []

    def extract_raw(self, file_path: str) -> ExtractResult:
        """Extract raw text and PDF metadata from document

        Args:
            file_path: Path to the document file

        Returns:
            ExtractResult with raw text, pages, and metadata
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
        """Extract raw text from PDF using pdfplumber"""
        pages = []
        pdf_metadata = {}

        try:
            with pdfplumber.open(file_path) as pdf:
                # Extract PDF metadata
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

                # Extract text from each page
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""

                    pages.append({
                        'text': page_text,
                        'page': page_num,
                        'chars': len(page_text),
                        'lines': len(page_text.split('\n')),
                    })

            # Combine all page texts
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
        """Extract raw text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            # Split into pages by form feed or large sections
            pages = []
            sections = text.split('\f') if '\f' in text else [text]

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
            # Try other encodings
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
        """Extract raw text from DOCX file"""
        try:
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

        except Exception as e:
            logger.error(f'Error extracting DOCX: {e}', exc_info=True)
            raise

    def clean(self, raw_data: ExtractResult, options: CleaningOptions = None) -> CleaningResult:
        """Execute cleaning on extracted raw data

        Args:
            raw_data: ExtractResult from extract_raw()
            options: CleaningOptions to control cleaning behavior

        Returns:
            CleaningResult with cleaned text and statistics
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

        # Calculate statistics
        original_chars = len(original_text)
        cleaned_chars = len(cleaned_text)
        removed_chars_count = original_chars - cleaned_chars
        reduction_percent = (removed_chars_count / original_chars * 100) if original_chars > 0 else 0

        # Extract metadata from PDF and cleaned text
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
        """Preview cleaning effect with before/after comparison

        Args:
            raw_data: ExtractResult from extract_raw()
            options: CleaningOptions to control cleaning behavior

        Returns:
            Dict with preview data for visualization
        """
        result = self.clean(raw_data, options)

        # Create line-by-line diff for visualization
        original_lines = result.original_text.split('\n')
        cleaned_lines = result.cleaned_text.split('\n')

        # Mark deleted lines in original
        deleted_line_set = set(result.removed_lines)

        diff_result = []
        original_idx = 0
        cleaned_idx = 0

        while original_idx < len(original_lines) or cleaned_idx < len(cleaned_lines):
            orig_line = original_lines[original_idx] if original_idx < len(original_lines) else None
            clean_line = cleaned_lines[cleaned_idx] if cleaned_idx < len(cleaned_lines) else None

            if orig_line and orig_line.strip() in deleted_line_set:
                # This line was removed
                diff_result.append({
                    'type': 'removed',
                    'original': orig_line,
                    'cleaned': None,
                    'original_line_num': original_idx + 1,
                })
                original_idx += 1
            elif orig_line == clean_line:
                # Line unchanged
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
                # Line modified (e.g., OCR correction)
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
                # New line added (unlikely in cleaning)
                diff_result.append({
                    'type': 'added',
                    'original': None,
                    'cleaned': clean_line,
                    'cleaned_line_num': cleaned_idx + 1,
                })
                cleaned_idx += 1
            else:
                # Advance both
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
            'diff': diff_result[:500],  # Limit diff for preview (first 500 lines)
            'total_diff_lines': len(diff_result),
        }

    def _detect_repeated_lines(self, pages: List[Dict], threshold: float = 0.5) -> set:
        """Detect header/footer lines that appear in multiple pages

        Args:
            pages: List of page data dicts
            threshold: Minimum fraction of pages for a line to be considered repeated

        Returns:
            Set of repeated lines to filter
        """
        if not pages:
            return set()

        line_counts = Counter()
        for page_data in pages:
            lines = set(page_data['text'].strip().split('\n'))
            for line in lines:
                stripped = line.strip()
                if stripped and len(stripped) < 100:  # Ignore long lines
                    line_counts[stripped] += 1

        # Lines appearing in more than threshold% of pages
        min_count = int(len(pages) * threshold)
        repeated = {line for line, count in line_counts.items()
                   if count >= max(min_count, 2) and len(line) < 100}

        logger.info(f'Detected {len(repeated)} repeated lines (headers/footers)')
        return repeated

    def _remove_repeated_lines(self, text: str, repeated_lines: set) -> tuple:
        """Remove repeated header/footer lines from text

        Returns:
            (cleaned_text, list of removed lines)
        """
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

    def _remove_page_numbers(self, text: str) -> tuple:
        """Remove page number lines from text

        Returns:
            (cleaned_text, list of removed lines)
        """
        lines = text.split('\n')
        cleaned = []
        removed = []

        for line in lines:
            stripped = line.strip()
            is_page_num = False
            for pattern in self.PAGE_NUMBER_PATTERNS:
                if re.match(pattern, stripped, re.IGNORECASE):
                    is_page_num = True
                    break

            if is_page_num:
                removed.append(stripped)
            else:
                cleaned.append(line)

        return '\n'.join(cleaned), removed

    def _clean_noise_chars(self, text: str) -> tuple:
        """Clean noise characters from text

        Returns:
            (cleaned_text, count of changes)
        """
        count = 0
        cleaned = text

        for pattern in self.NOISE_PATTERNS:
            matches = re.findall(pattern, cleaned, re.MULTILINE)
            count += len(matches)
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)

        return cleaned, count

    def _ocr_postprocess(self, text: str) -> tuple:
        """Apply OCR post-processing corrections

        Returns:
            (cleaned_text, count of corrections)
        """
        count = 0
        cleaned = text

        for pattern, replacement in self.OCR_CORRECTIONS.items():
            matches = re.findall(pattern, cleaned)
            if matches:
                count += len(matches)
                cleaned = re.sub(pattern, replacement, cleaned)

        return cleaned, count

    def _normalize_whitespace(self, text: str) -> tuple:
        """Normalize whitespace in text

        Returns:
            (cleaned_text, count of changes)
        """
        count = 0

        # Replace multiple spaces with single space
        original_len = len(text)
        cleaned = re.sub(r'[ \t]+', ' ', text)

        # Remove trailing whitespace from lines
        lines = cleaned.split('\n')
        lines = [line.rstrip() for line in lines]
        cleaned = '\n'.join(lines)

        # Remove multiple blank lines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        count = original_len - len(cleaned)
        return cleaned, count

    def _filter_non_content(self, text: str) -> tuple:
        """Filter non-content lines (ads, very short lines, etc.)

        Returns:
            (cleaned_text, list of removed lines)
        """
        lines = text.split('\n')
        cleaned = []
        removed = []

        for line in lines:
            stripped = line.strip()

            # Skip empty lines (but preserve one for paragraph separation)
            if not stripped:
                # Keep paragraph separation
                if cleaned and cleaned[-1].strip():
                    cleaned.append(line)
                continue

            # Skip very short lines that are ONLY numbers/dots (like "...." or "---")
            # But preserve short titles like "前言", "墨菲定律"
            if len(stripped) < 3 and re.match(r'^[\d\.\s\-\*]+$', stripped):
                removed.append(stripped)
                continue

            # DON'T remove numbered list items like "1." or "1. xxx"
            # The previous logic was too aggressive
            # Only remove if it's truly garbage (just dots/numbers with no content)
            if re.match(r'^\.\.\.\.\.*$', stripped):  # Only dots
                removed.append(stripped)
                continue

            cleaned.append(line)

        return '\n'.join(cleaned), removed

    def _extract_metadata(self, raw_data: ExtractResult, cleaned_text: str) -> Dict[str, Any]:
        """Extract metadata from PDF and cleaned text

        Returns:
            Dict with extracted metadata
        """
        metadata = {
            'title': '',
            'author': '',
            'date': '',
            'category': '',
            'source': '',
            'page_count': 0,
        }

        # Get PDF metadata if available
        if raw_data.pdf_metadata:
            metadata['title'] = raw_data.pdf_metadata.get('title', '')
            metadata['author'] = raw_data.pdf_metadata.get('author', '')
            metadata['page_count'] = raw_data.pdf_metadata.get('page_count', 0)

            # Try to parse date from PDF metadata
            creation_date = raw_data.pdf_metadata.get('creation_date', '')
            if creation_date:
                # PDF dates are like "D:20240101120000"
                try:
                    if creation_date.startswith('D:'):
                        date_str = creation_date[2:10]  # Get YYYYMMDD
                        metadata['date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                except:
                    pass

        # Try to extract title from first meaningful line if not in PDF metadata
        if not metadata['title']:
            lines = cleaned_text.strip().split('\n')
            for line in lines[:10]:  # Check first 10 lines
                stripped = line.strip()
                if len(stripped) > 10 and len(stripped) < 100:
                    # Likely a title
                    metadata['title'] = stripped
                    break

        return metadata


# Global instance
document_cleaner = DocumentCleaner()