## ADDED Requirements

### Requirement: Document parsing pipeline
The system SHALL provide a document parsing pipeline in `rag/offline/parsers/` that extracts text from PDF, Word, and Excel files.

#### Scenario: PDF document parsed
- **WHEN** a PDF file is provided to `rag/offline/parsers/pdf.py`
- **THEN** the parser returns extracted text content with page-level metadata

#### Scenario: Word document parsed
- **WHEN** a .docx file is provided to `rag/offline/parsers/word.py`
- **THEN** the parser returns extracted text content

#### Scenario: Excel spreadsheet parsed
- **WHEN** a .xlsx file is provided to `rag/offline/parsers/excel.py`
- **THEN** the parser returns extracted tabular content as structured text

### Requirement: Document cleaning
The system SHALL provide document cleaning in `rag/offline/cleaning.py` that normalizes whitespace, removes artifacts, and preserves meaningful structure.

#### Scenario: Text cleaned from PDF artifacts
- **WHEN** raw text with excessive whitespace and control characters is provided
- **THEN** the cleaner returns normalized text with single spaces and no control characters

### Requirement: Document chunking
The system SHALL provide text chunking in `rag/offline/chunking.py` using recursive character splitting to produce semantically coherent chunks.

#### Scenario: Text split into chunks
- **WHEN** a long document text is provided with a target chunk size
- **THEN** the chunker returns overlapping text chunks that respect sentence boundaries

### Requirement: Embedding generation
The system SHALL provide embedding generation in `rag/offline/embedding.py` that converts text chunks to dense vectors using a configurable embedding model.

#### Scenario: Chunks converted to vectors
- **WHEN** a list of text chunks is provided
- **THEN** the embedder returns a corresponding list of dense vector embeddings

### Requirement: Vector indexing
The system SHALL provide vector indexing in `rag/offline/indexing.py` that persists embeddings and metadata to ChromaDB.

#### Scenario: Vectors indexed to ChromaDB
- **WHEN** embeddings and their source metadata are provided
- **THEN** the indexer writes them to the ChromaDB collection and returns document IDs

### Requirement: Parent document store
The system SHALL provide a parent document store in `rag/offline/parent_store.py` that maps small chunks back to their parent documents for Small-to-Big retrieval.

#### Scenario: Parent document retrieved for a child chunk
- **WHEN** a child chunk ID is queried
- **THEN** the parent store returns the full parent document text and metadata

### Requirement: Offline pipeline orchestration
The system SHALL provide an offline pipeline in `rag/offline/pipeline.py` that orchestrates parsing → cleaning → chunking → embedding → indexing as a single entry point.

#### Scenario: Full document ingestion executed
- **WHEN** a document file path is provided to the offline pipeline
- **THEN** the pipeline executes all stages in order and returns indexing confirmation
