"""
RAGAS Evaluation Runner for SupportPilot.

Runs the RAG pipeline against test cases and computes RAGAS metrics.
Entry point: python -m evaluation.run_evaluation [options]

Usage:
    python -m evaluation.run_evaluation --limit 10 --parallel 4
    python -m evaluation.run_evaluation --category comparison
    python -m evaluation.run_evaluation --output /tmp/my_report.json
"""
import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Ensure project root on path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Load .env for API keys
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_project_root, ".env"))
except ImportError:
    pass

logger = logging.getLogger("evaluation")


def setup_logging(verbose: bool = False):
    """Configure logging for evaluation runs."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(handler)
    logger.setLevel(level)
    # Keep noisy libraries quiet
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


def _mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _min(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return round(min(values), 4)


def _max(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return round(max(values), 4)


def _std(values: List[float]) -> Optional[float]:
    if not values or len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return round(variance ** 0.5, 4)


class EvaluationRunner:
    """Runs RAG evaluation over a test case set and produces a report."""

    METRICS = [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]

    def __init__(self, config_path: Optional[str] = None, output_dir: Optional[str] = None):
        self._config_path = config_path or os.path.join(_project_root, "config", "rag_config.yaml")
        self._output_dir = output_dir or os.path.join(os.path.dirname(__file__), "reports")
        self._metrics = None
        self._rag_service = None
        self._app = None
        self._app_context = None
        self._init_app_context()

    def _init_app_context(self):
        """Initialize Flask app context for DB access during evaluation.

        RAGService._log_retrieval() writes to the database, which requires
        a Flask application context. We create one here and keep it alive
        for the duration of the evaluation run.
        """
        try:
            from app import create_app
            self._app = create_app()
            self._app_context = self._app.app_context()
            self._app_context.push()
            logger.debug("Flask app context initialized for evaluation")
        except Exception as e:
            logger.warning("Failed to initialize Flask app context: %s", e)
            self._app = None
            self._app_context = None

    # ---- lazy inits (no Flask context needed) ----

    @property
    def rag_service(self):
        if self._rag_service is None:
            from rag.online.service import RAGService
            self._rag_service = RAGService()
        return self._rag_service

    @property
    def metrics(self):
        if self._metrics is None:
            from evaluation.metrics import RagasMetrics
            self._metrics = RagasMetrics()
        return self._metrics

    # ---- test case loading ----

    def load_cases(self) -> List[Dict]:
        """Load test cases from cases.json."""
        cases_path = os.path.join(os.path.dirname(__file__), "test_cases", "cases.json")
        try:
            with open(cases_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cases = data.get("cases", [])
            logger.info("Loaded %d test cases from %s", len(cases), cases_path)
            return cases
        except FileNotFoundError:
            logger.error("Test cases file not found: %s", cases_path)
            return []
        except json.JSONDecodeError as e:
            logger.error("Invalid test cases JSON: %s", e)
            return []

    # ---- single-query execution ----

    def execute_query(self, case: Dict) -> Dict:
        """Execute one test case through the RAG pipeline.

        Returns a dict with: id, category, difficulty, query, contexts, answer,
        route_type, context_count, legacy_judge, error (if any).
        """
        query = case["query"]
        result = {
            "id": case["id"],
            "category": case["category"],
            "difficulty": case.get("difficulty", "medium"),
            "query": query,
            "expected_topics": case.get("expected_topics", []),
            "contexts": [],
            "answer": "",
            "route_type": "unknown",
            "context_count": 0,
            "legacy_judge": None,
            "duration_ms": 0,
            "error": None,
        }

        t_start = time.time()

        try:
            # Step 1: retrieve contexts
            contexts = self.rag_service.retrieve(query=query, k=5)
            result["context_count"] = len(contexts)
            context_texts = [c.get("content", "") for c in contexts]
            result["contexts"] = context_texts

            # Step 2: determine route type
            try:
                from rag.online.router import query_router
                route_type, _ = query_router.route(query)
                result["route_type"] = route_type
            except Exception:
                result["route_type"] = "simple"

            # Step 3: generate answer
            if result["route_type"] == "agentic":
                try:
                    from rag.online.pipeline.builder import retrieval_agent
                    agent_result = retrieval_agent.run(query)
                    result["answer"] = agent_result.get("answer", "") or ""
                except Exception as e:
                    logger.warning("Agentic path failed for %s: %s", case["id"], e)
                    result["answer"] = self._generate_simple(query, contexts)
            else:
                result["answer"] = self._generate_simple(query, contexts)

            # Step 4: legacy LLM-as-Judge
            try:
                from evaluation.rag_evaluation import judge_retrieval
                result["legacy_judge"] = judge_retrieval(query, contexts)
            except Exception as e:
                logger.debug("Legacy judge failed for %s: %s", case["id"], e)

        except Exception as e:
            logger.error("Query execution failed for %s: %s", case["id"], e)
            result["error"] = str(e)

        result["duration_ms"] = round((time.time() - t_start) * 1000, 1)
        return result

    @staticmethod
    def _generate_simple(query: str, contexts: List[Dict]) -> str:
        """Generate an answer using llm_client.chat() for simple-route queries."""
        try:
            from llm.llm_client import llm_client
            return llm_client.chat(
                query=query,
                context=contexts,
                temperature=0.1,
                max_tokens=512,
            )
        except Exception as e:
            logger.warning("Simple generation failed: %s", e)
            return ""

    # ---- RAGAS computation ----

    def evaluate_case(self, case_result: Dict, ground_truth: Optional[str] = None) -> Dict:
        """Compute RAGAS metrics for a single executed case.

        Args:
            case_result: Result from execute_query
            ground_truth: Optional reference answer for context_precision/context_recall
        """
        ragas_scores = {
            "faithfulness": None,
            "context_precision": None,
            "context_recall": None,
            "answer_relevancy": None,
        }

        if case_result.get("error"):
            ragas_scores["error"] = case_result["error"]
            return ragas_scores

        question = case_result["query"]
        contexts = case_result.get("contexts", [])
        answer = case_result.get("answer", "")

        if not answer or not contexts:
            return ragas_scores

        try:
            scores = self.metrics.compute_all(
                question, contexts, answer, ground_truth=ground_truth
            )
            ragas_scores.update(scores)
        except Exception as e:
            logger.warning("RAGAS failed for %s: %s", case_result["id"], e)
            ragas_scores["error"] = str(e)

        return ragas_scores

    def execute_and_evaluate(self, case: Dict) -> Dict:
        """Execute query, then compute RAGAS metrics. Returns combined result.

        Pushes Flask app context per-thread so DB logging works in threaded mode.
        """
        if self._app is not None:
            with self._app.app_context():
                return self._execute_and_evaluate_impl(case)
        return self._execute_and_evaluate_impl(case)

    def _execute_and_evaluate_impl(self, case: Dict) -> Dict:
        """Inner implementation of execute + evaluate."""
        result = self.execute_query(case)
        ragas = self.evaluate_case(result, ground_truth=case.get("reference"))
        result.update(ragas)
        return result

    # ---- aggregation ----

    def aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate per-case results into overall and per-category statistics."""
        successful = [r for r in results if not r.get("error")]
        failed = [r for r in results if r.get("error")]

        overall = self._aggregate_group(successful)
        by_category = {}
        by_difficulty = {}

        categories = sorted(set(r["category"] for r in results))
        for cat in categories:
            group = [r for r in successful if r["category"] == cat]
            if group:
                by_category[cat] = self._aggregate_group(group)
                by_category[cat]["count"] = len(group)

        difficulties = sorted(set(r.get("difficulty", "medium") for r in results))
        for diff in difficulties:
            group = [r for r in successful if r.get("difficulty") == diff]
            if group:
                by_difficulty[diff] = self._aggregate_group(group)
                by_difficulty[diff]["count"] = len(group)

        # Route type distribution
        route_dist = {}
        for r in results:
            rt = r.get("route_type", "unknown")
            route_dist[rt] = route_dist.get(rt, 0) + 1

        return {
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_cases": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "route_distribution": route_dist,
            },
            "overall": overall,
            "by_category": by_category,
            "by_difficulty": by_difficulty,
        }

    def _aggregate_group(self, items: List[Dict]) -> Dict:
        """Compute aggregate statistics for a group of case results."""
        agg = {"count": len(items)}
        for metric in self.METRICS:
            values = [r[metric] for r in items if r.get(metric) is not None]
            agg[metric] = {
                "mean": _mean(values),
                "min": _min(values),
                "max": _max(values),
                "std": _std(values),
                "samples": len(values),
            }
        return agg

    # ---- report output ----

    def write_report(self, report: Dict, filepath: Optional[str] = None) -> str:
        """Write the full evaluation report as JSON."""
        os.makedirs(self._output_dir, exist_ok=True)

        if filepath is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self._output_dir, f"{ts}_report.json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info("Report written to %s", filepath)
        return filepath

    def print_summary(self, report: Dict):
        """Print a console summary table."""
        print()
        print("=" * 72)
        print("   RAGAS Evaluation Report - SupportPilot")
        print("=" * 72)

        meta = report.get("meta", {})
        print(f"   Total: {meta.get('total_cases', 0)}  |  "
              f"Success: {meta.get('successful', 0)}  |  "
              f"Failed: {meta.get('failed', 0)}")
        route_dist = meta.get("route_distribution", {})
        if route_dist:
            route_str = "  ".join(f"{k}: {v}" for k, v in sorted(route_dist.items()))
            print(f"   Routes: {route_str}")
        print("-" * 72)

        # Column header
        header = f"  {'Category':<16s} | {'Faith.':>6s} | {'Prec.':>6s} | {'Recall':>6s} | {'Relev.':>6s} | n  "
        print(header)
        print("-" * 72)

        # Per-category rows
        by_category = report.get("by_category", {})
        for cat in sorted(by_category.keys()):
            stats = by_category[cat]
            self._print_metric_row(cat, stats)

        print("-" * 72)
        # Overall row
        overall = report.get("overall", {})
        self._print_metric_row("OVERALL", overall)
        print("-" * 72)

        # Difficulty breakdown
        by_diff = report.get("by_difficulty", {})
        if by_diff:
            print("   Difficulty Breakdown:")
            for diff in sorted(by_diff.keys()):
                stats = by_diff[diff]
                self._print_metric_row(f"    {diff}", stats)
            print("-" * 72)

        # Legacy judge correlation (if available)
        legacy_scores = []
        faith_scores = []
        for case in report.get("cases", []):
            lj = case.get("legacy_judge")
            fv = case.get("faithfulness")
            if lj and lj.get("judge_score") and fv is not None:
                js = lj["judge_score"]
                avg = (js.get("relevance", 0) + js.get("completeness", 0) + js.get("noise", 0)) / 3
                legacy_scores.append(avg)
                faith_scores.append(fv)

        if legacy_scores:
            avg_legacy = round(sum(legacy_scores) / len(legacy_scores), 2)
            print(f"   Legacy Judge (avg 1-5): {avg_legacy}  (n={len(legacy_scores)})")

        print("=" * 72)
        print()

    @staticmethod
    def _print_metric_row(label: str, stats: Dict):
        """Print one row of the summary table."""
        def _val(key):
            m = stats.get(key)
            if isinstance(m, dict):
                v = m.get("mean")
                return f"{v:.3f}" if v is not None else "  N/A "
            return "  N/A "

        n = stats.get("count", 0)
        print(f"  {label:<16s} | {_val('faithfulness'):>6s} | "
              f"{_val('context_precision'):>6s} | {_val('context_recall'):>6s} | "
              f"{_val('answer_relevancy'):>6s} | {n:>2d}")

    # ---- main loop ----

    def run(self, limit: Optional[int] = None, parallel: int = 4,
            category: Optional[str] = None) -> Dict:
        """Run the full evaluation pipeline.

        Args:
            limit: Maximum number of test cases to run.
            parallel: Number of concurrent workers.
            category: Run only cases from this category.

        Returns:
            Full evaluation report dict.
        """
        cases = self.load_cases()
        if not cases:
            logger.error("No test cases loaded. Aborting.")
            return {}

        # Filter by category
        if category:
            cases = [c for c in cases if c["category"] == category]
            if not cases:
                logger.error("No cases found for category: %s", category)
                return {}
            logger.info("Filtered to %d cases in category '%s'", len(cases), category)

        if limit and limit < len(cases):
            cases = cases[:limit]
            logger.info("Limited to %d cases", limit)

        logger.info("Starting evaluation: %d cases, %d workers", len(cases), parallel)

        results = []
        completed = 0

        try:
            if parallel > 1 and len(cases) > 1:
                with ThreadPoolExecutor(max_workers=parallel) as executor:
                    future_map = {
                        executor.submit(self.execute_and_evaluate, case): case
                        for case in cases
                    }
                    for future in as_completed(future_map):
                        case = future_map[future]
                        try:
                            result = future.result(timeout=120)
                            results.append(result)
                        except Exception as e:
                            logger.error("Case %s failed: %s", case["id"], e)
                            results.append({
                                "id": case["id"],
                                "category": case.get("category", "unknown"),
                                "error": str(e),
                            })
                        completed += 1
                        logger.info("Progress: %d/%d (%s)", completed, len(cases), case["id"])
            else:
                for case in cases:
                    result = self.execute_and_evaluate(case)
                    results.append(result)
                    completed += 1
                    logger.info("Progress: %d/%d (%s)", completed, len(cases), case["id"])

            # Build report
            aggregated = self.aggregate_results(results)
            report = {**aggregated, "cases": results}

            # Write to disk
            filepath = self.write_report(report)

            # Print summary
            self.print_summary(report)

            logger.info("Evaluation complete. Report: %s", filepath)
            return report
        finally:
            if self._app_context is not None:
                self._app_context.pop()
                logger.debug("Flask app context popped")


def main():
    parser = argparse.ArgumentParser(
        description="SupportPilot RAGAS Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m evaluation.run_evaluation --limit 5\n"
            "  python -m evaluation.run_evaluation --category comparison\n"
            "  python -m evaluation.run_evaluation --parallel 4 --output /tmp/report.json\n"
        ),
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Max test cases to run (default: all)")
    parser.add_argument("--parallel", type=int, default=4,
                        help="Concurrent workers (default: 4)")
    parser.add_argument("--category", type=str, default=None,
                        help="Run only cases from this category")
    parser.add_argument("--output", type=str, default=None,
                        help="Custom JSON report path")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    # Verify API key is available
    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        logger.warning(
            "LLM_API_KEY not set in environment. "
            "RAGAS LLM-based metrics (faithfulness, relevancy, recall) will fail. "
            "Set it via: export LLM_API_KEY=...  or ensure it's in .env"
        )

    runner = EvaluationRunner(output_dir=args.output)
    report = runner.run(
        limit=args.limit,
        parallel=args.parallel,
        category=args.category,
    )

    if not report:
        sys.exit(1)


if __name__ == "__main__":
    main()
