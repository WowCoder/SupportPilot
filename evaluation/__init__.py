"""Evaluation module: RAGAS metrics + legacy LLM-as-Judge + test runner."""

from evaluation.rag_evaluation import judge_retrieval, JUDGE_SYSTEM_PROMPT

from evaluation.metrics import (
    RagasLLMAdapter,
    RagasMetrics,
    compute_faithfulness,
    compute_context_precision,
    compute_context_recall,
    compute_answer_relevancy,
    compute_all_metrics,
)

__all__ = [
    # Legacy LLM-as-Judge
    "judge_retrieval",
    "JUDGE_SYSTEM_PROMPT",
    # RAGAS metrics
    "RagasLLMAdapter",
    "RagasMetrics",
    "compute_faithfulness",
    "compute_context_precision",
    "compute_context_recall",
    "compute_answer_relevancy",
    "compute_all_metrics",
    # Runner (lazy import to avoid -m conflict)
    "EvaluationRunner",
]


def __getattr__(name):
    if name == "EvaluationRunner":
        from evaluation.run_evaluation import EvaluationRunner
        return EvaluationRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
