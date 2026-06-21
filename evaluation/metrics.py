"""
RAGAS metrics integration for SupportPilot RAG evaluation.

Provides wrappers for RAGAS 0.4.x metrics:
- faithfulness: whether the answer is grounded in retrieved contexts
- context_precision: signal-to-noise ratio in retrieved chunks
- context_recall: coverage of needed information (requires ground_truth)
- answer_relevancy: how well the answer addresses the query

Also provides a RagasLLMAdapter that bridges RAGAS's LangChain LLM expectation
with SupportPilot's existing OpenAI-compatible API (DeepSeek-v4-flash).
"""
import logging
import os
import sys
from typing import Dict, List, Optional

# ---- Monkey-patch: RAGAS 0.4.3 has a hard import of langchain_community.chat_models.vertexai
# which may not be available. Provide a shim to prevent import errors. ----
if "langchain_community.chat_models.vertexai" not in sys.modules:
    _shim = type(sys)("langchain_community.chat_models.vertexai")
    _shim.ChatVertexAI = None
    sys.modules["langchain_community.chat_models.vertexai"] = _shim

# Ensure HF mirror for embedding model downloads (consistent with pipeline.py)
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

logger = logging.getLogger(__name__)


class RagasLLMAdapter:
    """RAGAS 0.4.x LLM adapter using llm_factory + OpenAI client.

    RAGAS 0.4.x metrics (Faithfulness, AnswerRelevancy, etc.) expect an
    InstructorBaseRagasLLM instance. This adapter uses ragas.llms.llm_factory()
    with an OpenAI client pointed at DeepSeek's OpenAI-compatible API.

    The adapter reads config from llm_config.yaml and environment, reusing
    the same API endpoint as SupportPilot's llm_client.
    """

    def __init__(self):
        self._llm = None
        self._model = None

    @property
    def llm(self):
        """Lazy-initialize an InstructorBaseRagasLLM via llm_factory.

        Uses provider="openai" because DeepSeek is fully OpenAI-compatible
        (same /chat/completions endpoint format). The instructor library
        handles structured output extraction (Mode.JSON) for RAGAS metrics.
        """
        if self._llm is None:
            from openai import OpenAI
            from ragas.llms import llm_factory

            api_base, api_key, model = self._read_config()
            self._model = model

            client = OpenAI(
                api_key=api_key,
                base_url=api_base.rstrip("/") if api_base else None,
                timeout=60,
            )
            self._llm = llm_factory(
                model=model,
                provider="openai",
                client=client,
                max_tokens=4096,
            )
            logger.info("RagasLLMAdapter initialized: model=%s base=%s", model, api_base)

        return self._llm

    @property
    def model_name(self) -> str:
        if self._model is None:
            # Trigger lazy init
            _ = self.llm
        return self._model or "unknown"

    @staticmethod
    def _read_config():
        """Read API config from llm_config.yaml and environment.

        Returns:
            Tuple of (api_base, api_key, model)
        """
        import yaml

        # Try loading .env if API key not already in environment
        if not os.environ.get("LLM_API_KEY"):
            try:
                from dotenv import load_dotenv
                # evaluation/metrics.py → evaluation/ → project_root/
                _project_root = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__)))
                load_dotenv(os.path.join(_project_root, ".env"))
            except ImportError:
                pass

        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "llm_config.yaml"
        )
        config = {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning("llm_config.yaml not found at %s, using defaults", config_path)

        provider = config.get("provider", "openai_compatible")
        provider_cfg = config.get(provider, {})
        defaults = config.get("defaults", {})

        api_base = provider_cfg.get("api_base", "")
        model = provider_cfg.get("model", defaults.get("model", "deepseek-v4-flash"))

        # API key: check env var referenced by config, then env fallback
        key_env = provider_cfg.get("api_key_env", "")
        api_key = os.environ.get(key_env, "") if key_env else ""
        if not api_key:
            api_key = os.environ.get("LLM_API_KEY", "")

        return api_base, api_key, model


def _get_embeddings():
    """Get LangChain-compatible embeddings for RAGAS embedding-based metrics.

    Returns a HuggingFaceEmbeddings instance. Tries bge-large-zh-v1.5 first
    for Chinese support, falls back to BAAI/bge-m3.
    """
    from langchain_huggingface import HuggingFaceEmbeddings

    model_name = os.environ.get("RAGAS_EMBEDDING_MODEL", "BAAI/bge-m3")
    try:
        logger.info("Loading embedding model: %s", model_name)
        emb = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        # Quick warm-up to verify model works
        _ = emb.embed_query("测试")
        logger.info("Embedding model loaded: %s", model_name)
        return emb
    except Exception:
        logger.warning(
            "Failed to load %s, falling back to BAAI/bge-m3", model_name
        )
        fallback = "BAAI/bge-m3"
        return HuggingFaceEmbeddings(
            model_name=fallback,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )


class RagasMetrics:
    """Container for RAGAS metrics with Chinese-optimized configuration.

    Usage:
        metrics = RagasMetrics()
        scores = metrics.compute_all(question="...", contexts=["..."], answer="...")
        # scores = {"faithfulness": 0.85, "context_precision": 0.72, ...}
    """

    def __init__(self, llm=None, embeddings=None):
        self._llm = llm
        self._embeddings = embeddings

    @property
    def llm(self):
        if self._llm is None:
            self._llm = RagasLLMAdapter().llm
        return self._llm

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = _get_embeddings()
        return self._embeddings

    def compute_all(self, question: str, contexts: List[str], answer: str,
                    ground_truth: Optional[str] = None) -> Dict[str, Optional[float]]:
        """Compute all available RAGAS metrics for a single query.

        Args:
            question: User query string
            contexts: List of retrieved context strings
            answer: Generated answer string
            ground_truth: Optional reference answer (required for context_precision
                         and context_recall)

        Returns:
            Dict with metric names as keys and float scores (or None on failure).
            Keys: faithfulness, context_precision, context_recall, answer_relevancy
        """
        from ragas import SingleTurnSample
        from ragas.metrics import (
            Faithfulness,
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
        )

        if not answer or not contexts:
            return {
                "faithfulness": None,
                "context_precision": None,
                "context_recall": None,
                "answer_relevancy": None,
                "error": "Missing answer or contexts",
            }

        scores = {
            "faithfulness": None,
            "context_precision": None,
            "context_recall": None,
            "answer_relevancy": None,
        }

        try:
            sample = SingleTurnSample(
                user_input=question,
                retrieved_contexts=contexts,
                response=answer,
                reference=ground_truth or "",
            )

            # Faithfulness (answer vs contexts — no reference needed)
            try:
                faith_metric = Faithfulness(llm=self.llm)
                scores["faithfulness"] = round(
                    float(faith_metric.single_turn_score(sample)), 4
                )
            except Exception:
                logger.warning("Faithfulness failed", exc_info=True)

            # Answer Relevancy (needs embeddings)
            try:
                relev_metric = AnswerRelevancy(
                    llm=self.llm, embeddings=self.embeddings
                )
                scores["answer_relevancy"] = round(
                    float(relev_metric.single_turn_score(sample)), 4
                )
            except Exception:
                logger.warning("AnswerRelevancy failed", exc_info=True)

            # Context Precision + Context Recall (both need reference, llm only)
            if ground_truth:
                try:
                    cp_metric = ContextPrecision(llm=self.llm)
                    scores["context_precision"] = round(
                        float(cp_metric.single_turn_score(sample)), 4
                    )
                except Exception:
                    logger.warning("ContextPrecision failed", exc_info=True)

                try:
                    cr_metric = ContextRecall(llm=self.llm)
                    scores["context_recall"] = round(
                        float(cr_metric.single_turn_score(sample)), 4
                    )
                except Exception:
                    logger.warning("ContextRecall failed", exc_info=True)

        except Exception:
            logger.error(
                "RAGAS evaluation failed for query: %s", question[:80],
                exc_info=True,
            )
            scores["error"] = "RAGAS evaluation failed"

        return scores


# Module-level convenience functions

_metrics_instance = None


def _get_metrics() -> RagasMetrics:
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = RagasMetrics()
    return _metrics_instance


def compute_faithfulness(question: str, contexts: List[str], answer: str) -> Optional[float]:
    """Compute faithfulness score for a single query."""
    result = _get_metrics().compute_all(question, contexts, answer)
    return result.get("faithfulness")


def compute_context_precision(question: str, contexts: List[str], answer: str) -> Optional[float]:
    """Compute context precision score for a single query."""
    result = _get_metrics().compute_all(question, contexts, answer)
    return result.get("context_precision")


def compute_context_recall(question: str, contexts: List[str], answer: str,
                           ground_truth: str) -> Optional[float]:
    """Compute context recall score (requires ground truth)."""
    result = _get_metrics().compute_all(question, contexts, answer, ground_truth=ground_truth)
    return result.get("context_recall")


def compute_answer_relevancy(question: str, contexts: List[str], answer: str) -> Optional[float]:
    """Compute answer relevancy score for a single query."""
    result = _get_metrics().compute_all(question, contexts, answer)
    return result.get("answer_relevancy")


def compute_all_metrics(question: str, contexts: List[str], answer: str,
                        ground_truth: Optional[str] = None) -> Dict[str, Optional[float]]:
    """Compute all RAGAS metrics for a single query."""
    return _get_metrics().compute_all(question, contexts, answer, ground_truth=ground_truth)
