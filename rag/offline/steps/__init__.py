"""
Pipeline stages: composable ETL stages for the RAG offline pipeline.

Each stage is a callable class: stage(items) → processed_items.
"""
from rag.offline.steps.embedding import CustomEmbeddingFunction, EmbeddingStage
from rag.offline.steps.cleaning import CleaningStage
from rag.offline.steps.chunking import ChunkingStage, ChunkResult
from rag.offline.steps.quality import QualityStage, QualityConfig
from rag.offline.steps.indexing import IndexingStage

__all__ = [
    'CustomEmbeddingFunction',
    'EmbeddingStage',
    'CleaningStage',
    'ChunkingStage',
    'ChunkResult',
    'QualityStage',
    'QualityConfig',
    'IndexingStage',
]
