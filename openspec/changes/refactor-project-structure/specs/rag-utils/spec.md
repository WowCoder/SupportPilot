## ADDED Requirements

### Requirement: RAG configuration loading
The system SHALL provide RAG configuration loading at `rag/utils/config.py` that reads `config/rag_config.yaml` and exposes typed configuration values.

#### Scenario: Config loaded from YAML
- **WHEN** the config loader is initialized
- **THEN** it reads retrieval parameters (top_k, threshold, weights) and pipeline limits (max_iterations, timeout, max_corrections) from the YAML file

#### Scenario: Config cached after first load
- **WHEN** the config has already been loaded
- **THEN** subsequent access returns cached values without re-reading the file

### Requirement: Execution observability
The system SHALL provide execution tracing at `rag/utils/observability.py` that records per-node timing, status, and metadata for each RAG query execution.

#### Scenario: Node execution traced
- **WHEN** a pipeline node completes execution
- **THEN** the tracer records node name, execution time, status (success/failure), and any node-specific metadata

#### Scenario: Trace persisted for dashboard
- **WHEN** a full query execution completes
- **THEN** the complete trace is persisted to the database for dashboard display

### Requirement: FAQ vector synchronization
The system SHALL provide FAQ vector synchronization at `rag/utils/faq_vector_sync.py` that keeps FAQ embeddings in sync with the FAQ entry database.

#### Scenario: New FAQ indexed
- **WHEN** a new FAQ entry is created in the database
- **THEN** the sync service generates its embedding and adds it to the FAQ ChromaDB collection

#### Scenario: FAQ removed from index
- **WHEN** an FAQ entry is deleted from the database
- **THEN** the sync service removes its corresponding vector from the ChromaDB collection

### Requirement: Tool base class
The system SHALL provide a tool base class at `rag/utils/container.py` that defines the common interface for RAG tools.

#### Scenario: Tool registered and executed
- **WHEN** a tool class inherits the base class and is registered
- **THEN** it can be invoked by the pipeline with standardized parameter passing and result formatting
