"""
Document parsers: format-specific parsers that produce ParsedPage objects.

Currently powered by Unstructured.io for broad format support.
"""
from rag.offline.parsers.base import BaseParser, ParsedPage
from rag.offline.parsers.unstructured_parser import UnstructuredParser, get_parser

__all__ = [
    'BaseParser',
    'ParsedPage',
    'UnstructuredParser',
    'get_parser',
]
