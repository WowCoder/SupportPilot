"""
Pipeline configuration dataclasses for the RAG offline ETL pipeline.

Each stage has its own config dataclass, nested under PipelineConfig.
"""
from dataclasses import dataclass, field


@dataclass
class ParsingConfig:
    """Configuration for document parsing (Unstructured-based)."""
    strategy: str = 'auto'          # 'auto' | 'fast' | 'hi_res' | 'ocr_only'
    languages: list = field(default_factory=lambda: ['chi_sim', 'eng'])
    encoding: str = 'utf-8'
    fallback_encodings: tuple = ('gbk', 'gb2312', 'latin-1')


@dataclass
class CleaningConfig:
    """Configuration for document cleaning stage."""
    remove_headers_footers: bool = True
    remove_page_numbers: bool = True
    clean_noise_chars: bool = True
    normalize_whitespace: bool = True
    ocr_postprocess: bool = True
    filter_non_content: bool = True
    repeated_line_threshold: float = 0.5
    min_line_length: int = 10


@dataclass
class ChunkingConfig:
    """Configuration for document chunking stage."""
    strategy: str = 'auto'           # 'auto' | 'sentence' | 'semantic' | 'recursive' | 'small_to_big'
    chunk_size: int = 1000
    chunk_overlap: int = 150
    parent_size: int = 2000
    child_size: int = 500
    semantic_threshold: float = 0.5
    min_chunk_chars: int = 20


@dataclass
class QualityConfig:
    """Configuration for quality scoring stage."""
    enabled: bool = True
    min_score: int = 60               # chunks below this score are discarded


@dataclass
class EmbeddingConfig:
    """Configuration for embedding model."""
    model_name: str = 'BAAI/bge-m3'
    device: str = 'cpu'


@dataclass
class IndexingConfig:
    """Configuration for ChromaDB indexing stage."""
    batch_size: int = 100
    dedup_enabled: bool = True
    collection_name: str = 'knowledge'
    hnsw_space: str = 'cosine'


@dataclass
class PipelineConfig:
    """Master configuration for the ETL pipeline."""
    parsing: ParsingConfig = field(default_factory=ParsingConfig)
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    indexing: IndexingConfig = field(default_factory=IndexingConfig)
