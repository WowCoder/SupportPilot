## ADDED Requirements

### Requirement: RAG service entry point
The system SHALL provide a RAG service entry point at `rag/online/service.py` that exposes a `retrieve()` method accepting a query and returning relevant document chunks.

#### Scenario: Query retrieves relevant documents
- **WHEN** a natural language query is passed to `RAGService.retrieve(query, k=3)`
- **THEN** the service returns up to `k` document chunks ranked by relevance with scores above the configured threshold

#### Scenario: Query routed to simple retrieval
- **WHEN** a query is classified as simple by the router
- **THEN** the service bypasses the agentic pipeline and performs direct retrieval

#### Scenario: Query routed to agentic retrieval
- **WHEN** a query is classified as complex by the router
- **THEN** the service invokes the full LangGraph pipeline with self-correction

### Requirement: Query router
The system SHALL provide query routing at `rag/online/router.py` that classifies queries and directs them to the appropriate retrieval strategy.

#### Scenario: Simple query detected by rule
- **WHEN** a query matches a rule-based pattern in `router_rules.py`
- **THEN** the router returns "simple" routing decision

#### Scenario: Complex query detected by classifier
- **WHEN** a query does not match rule patterns
- **THEN** the router invokes `router_classifier.py` using LLM classification and returns the routing decision

### Requirement: LangGraph pipeline
The system SHALL provide a LangGraph-based retrieval pipeline at `rag/online/pipeline/` that executes nodes for query understanding, tool selection, retrieval, validation, and synthesis with self-correction.

#### Scenario: Pipeline executes all nodes
- **WHEN** the pipeline is invoked with a query
- **THEN** it executes query_understanding → tool_selection → tool_execution → relevance_check → faithfulness_check → synthesis in sequence, with up to 3 correction iterations

#### Scenario: Pipeline corrects on relevance failure
- **WHEN** relevance_check determines retrieved documents are insufficient
- **THEN** the pipeline rewrites the query and re-executes retrieval, consuming one correction iteration

#### Scenario: Pipeline times out
- **WHEN** the pipeline exceeds 30 seconds of execution time
- **THEN** it returns partial results with a timeout indicator

### Requirement: Dense vector retrieval
The system SHALL provide dense vector retrieval at `rag/online/retrievers/dense.py` that searches ChromaDB using embedding similarity.

#### Scenario: Similar documents retrieved
- **WHEN** a query embedding is passed to the dense retriever
- **THEN** it returns the top-k most similar documents from ChromaDB with cosine similarity scores

### Requirement: BM25 sparse retrieval
The system SHALL provide BM25 sparse retrieval at `rag/online/retrievers/bm25.py` that performs keyword-based search.

#### Scenario: Keyword documents retrieved
- **WHEN** a query string is passed to the BM25 retriever
- **THEN** it returns the top-k documents ranked by BM25 score

### Requirement: Hybrid RRF fusion retrieval
The system SHALL provide hybrid retrieval at `rag/online/retrievers/hybrid.py` that fuses dense and sparse results using Reciprocal Rank Fusion.

#### Scenario: Dense and sparse results fused
- **WHEN** both dense and sparse retrieval results exist
- **THEN** the hybrid retriever merges and ranks them via RRF, returning combined results

### Requirement: Metadata filter
The system SHALL provide metadata filtering at `rag/online/retrievers/filter_tool.py` that narrows retrieval results by document-level metadata.

#### Scenario: Results filtered by document category
- **WHEN** retrieval results are passed with a metadata filter condition
- **THEN** only results matching the filter criteria are returned

### Requirement: Cross-encoder reranking
The system SHALL provide cross-encoder reranking at `rag/online/rerankers/cross_encoder.py` that scores query-document pairs for finer relevance ordering.

#### Scenario: Search results reranked
- **WHEN** a query and list of retrieved documents are passed to the reranker
- **THEN** the reranker returns documents reordered by cross-encoder relevance scores

### Requirement: LLM answer generation
The system SHALL provide LLM-based answer generation at `rag/online/generators/llm_generator.py` that synthesizes retrieved context into a natural language answer.

#### Scenario: Answer synthesized from context
- **WHEN** a query and retrieved document contexts are passed to the generator
- **THEN** it returns a coherent natural language answer citing the source documents

### Requirement: Retrieval observability
The system SHALL log each RAG query execution with node-level timing and status for dashboard display.

#### Scenario: Query execution logged
- **WHEN** a query completes (success or failure)
- **THEN** an execution trace with per-node timing, scores, and routing decisions is recorded
