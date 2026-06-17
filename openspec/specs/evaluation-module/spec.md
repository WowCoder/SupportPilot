## ADDED Requirements

### Requirement: Evaluation module independence
The system SHALL provide an evaluation module at `evaluation/` that operates independently of the Flask application layer.

#### Scenario: Evaluation runs without Flask context
- **WHEN** evaluation is executed via `python -m evaluation.run_evaluation`
- **THEN** it loads test cases, invokes RAG retrieval, computes metrics, and outputs results without requiring a running Flask server

### Requirement: RAGAS metrics computation
The system SHALL provide RAGAS metrics computation at `evaluation/metrics.py` that evaluates retrieval quality using standard metrics (faithfulness, relevance, context precision, context recall).

#### Scenario: Metrics computed for a test case
- **WHEN** a query, retrieved context, and reference answer are provided
- **THEN** the metrics module returns RAGAS scores for faithfulness, relevance, context precision, and recall

### Requirement: Test case management
The system SHALL store evaluation test cases at `evaluation/test_cases/cases.json` in a structured format with query, expected answer, and optional metadata.

#### Scenario: Test cases loaded
- **WHEN** the evaluation runner loads test cases
- **THEN** it parses cases.json containing at minimum query and reference_answer fields per case

### Requirement: Evaluation runner
The system SHALL provide an evaluation execution entry point at `evaluation/run_evaluation.py` that iterates through test cases, invokes RAG retrieval, computes metrics, and outputs a summary report.

#### Scenario: Full evaluation executed
- **WHEN** the evaluation runner is invoked with a test set
- **THEN** it runs each test case through RAG retrieval, computes all configured metrics, and outputs aggregated scores
