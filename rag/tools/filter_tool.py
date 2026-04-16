"""
Metadata Filter Tool for Agentic RAG system.

Supports filtering documents by metadata:
- Source file filtering
- Page number filtering
- Date range filtering
- Custom metadata key-value filtering
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from rag.core.tool import BaseTool, ToolResult
from rag.core.config import get_config

logger = logging.getLogger(__name__)


class MetadataFilterTool(BaseTool):
    """
    Metadata filter tool.

    Features:
    - Filter by source file
    - Filter by page number or page range
    - Filter by date range
    - Filter by custom metadata key-value pairs
    - Support for multiple filter conditions (AND logic)
    """

    name = "metadata_filter"
    description = "Filter documents by metadata such as source file, page number, or date range. Can be combined with other retrieval tools."

    def __init__(self):
        """Initialize the metadata filter tool."""
        self.config = get_config()

    def _match_filter(self, doc_metadata: Dict[str, Any], filter_config: Dict[str, Any]) -> bool:
        """
        Check if a document's metadata matches the filter criteria.

        Args:
            doc_metadata: Document's metadata dictionary
            filter_config: Filter criteria with key-value pairs

        Returns:
            True if document matches all filter conditions, False otherwise
        """
        for key, filter_value in filter_config.items():
            doc_value = doc_metadata.get(key)

            # Handle missing metadata
            if doc_value is None:
                # Check if filter has a default behavior for missing values
                if key not in doc_metadata:
                    # If filter specifies a value but doc doesn't have it, no match
                    # Unless filter_value is None or '*' (match all)
                    if filter_value is not None and filter_value != '*':
                        return False
                    continue

            # Handle different filter types
            if isinstance(filter_value, dict):
                # Complex filter operators
                if not self._apply_operator(doc_value, filter_value):
                    return False
            elif isinstance(filter_value, list):
                # List match: doc value should be in the list
                if doc_value not in filter_value:
                    return False
            elif filter_value != '*':
                # Exact match (skip '*' wildcard)
                if str(doc_value) != str(filter_value):
                    return False

        return True

    def _apply_operator(self, doc_value: Any, operator_config: Dict[str, Any]) -> bool:
        """
        Apply filter operator to a value.

        Args:
            doc_value: Document's metadata value
            operator_config: Operator configuration (e.g., {'gte': 1, 'lte': 10})

        Returns:
            True if operator condition is satisfied
        """
        result = True

        # Comparison operators
        if 'gte' in operator_config:
            result = result and (doc_value >= operator_config['gte'])

        if 'lte' in operator_config:
            result = result and (doc_value <= operator_config['lte'])

        if 'gt' in operator_config:
            result = result and (doc_value > operator_config['gt'])

        if 'lt' in operator_config:
            result = result and (doc_value < operator_config['lt'])

        if 'ne' in operator_config:
            result = result and (doc_value != operator_config['ne'])

        # Pattern matching
        if 'contains' in operator_config:
            result = result and (operator_config['contains'] in str(doc_value))

        if 'regex' in operator_config:
            import re
            result = result and bool(re.match(operator_config['regex'], str(doc_value)))

        # List membership
        if 'in' in operator_config:
            result = result and (doc_value in operator_config['in'])

        return result

    def execute(self,
                documents: List[Dict[str, Any]],
                source: str = None,
                pages: Any = None,
                date_from: str = None,
                date_to: str = None,
                custom_filters: Dict[str, Any] = None,
                **kwargs) -> ToolResult:
        """
        Filter documents by metadata.

        Args:
            documents: List of documents to filter
            source: Filter by source file name
            pages: Filter by page number or range (e.g., 5, "1-10", [1,2,3])
            date_from: Filter by date (ISO format string)
            date_to: Filter by date (ISO format string)
            custom_filters: Additional custom metadata filters

        Returns:
            ToolResult with filtered documents
        """
        try:
            if not documents:
                return ToolResult(success=True, data=[])

            # Build filter configuration
            filter_config = {}

            if source:
                filter_config['source'] = source

            if pages is not None:
                # Parse page filter
                if isinstance(pages, int):
                    filter_config['page'] = pages
                elif isinstance(pages, str) and '-' in pages:
                    # Range like "1-10"
                    start, end = map(int, pages.split('-'))
                    filter_config['page'] = {'gte': start, 'lte': end}
                elif isinstance(pages, list):
                    filter_config['page'] = {'in': pages}
                else:
                    filter_config['page'] = pages

            if date_from or date_to:
                date_filter = {}
                if date_from:
                    date_filter['gte'] = date_from
                if date_to:
                    date_filter['lte'] = date_to
                filter_config['date'] = date_filter

            if custom_filters:
                filter_config.update(custom_filters)

            # Apply filters
            filtered = []
            for doc in documents:
                doc_metadata = doc.get('metadata', {})

                # Handle special date filter
                if 'date' in filter_config:
                    date_filter = filter_config.pop('date')
                    doc_date = doc_metadata.get('date', '')
                    if doc_date:
                        if date_filter.get('gte') and doc_date < date_filter['gte']:
                            continue
                        if date_filter.get('lte') and doc_date > date_filter['lte']:
                            continue
                    else:
                        continue

                if self._match_filter(doc_metadata, filter_config):
                    filtered.append(doc)

            logger.debug(f'Metadata filter: {len(documents)} -> {len(filtered)} documents')
            return ToolResult(success=True, data=filtered)

        except Exception as e:
            logger.error(f'Metadata filter failed: {e}', exc_info=True)
            return ToolResult(success=False, error=str(e))


# Global instance
metadata_filter = MetadataFilterTool()
