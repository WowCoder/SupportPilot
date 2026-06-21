"""Run RAGAS smoke evaluation against ingested test_docs."""
import json
import logging
import os
import sys

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base)

# Load .env before other imports that may need env vars
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(base, ".env"))

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Load smoke cases
with open(os.path.join(base, "data", "smoke_cases.json")) as f:
    smoke = json.load(f)

from evaluation.run_evaluation import EvaluationRunner  # noqa: E402

runner = EvaluationRunner()

results = []
for case in smoke["cases"]:
    cid = case["id"]
    query = case["query"]
    print(f"  [{cid}] {query}")
    result = runner.execute_and_evaluate(case)
    results.append(result)

    faith = result.get("faithfulness")
    relev = result.get("answer_relevancy")
    cprec = result.get("context_precision")
    crecall = result.get("context_recall")
    ctxs = len(result.get("contexts", []))
    ans = result.get("answer", "")
    ans_preview = ans[:80].replace("\n", " ")
    print(f"    ctx={ctxs}  faith={faith}  relev={relev}  ct_prec={cprec}  ct_recall={crecall}")
    print(f"    answer={ans_preview!r}")

# Aggregate & report
agg = runner.aggregate_results(results)
report = {**agg, "cases": results}
filepath = runner.write_report(report)
runner.print_summary(report)
print(f"\nFull report: {filepath}")
