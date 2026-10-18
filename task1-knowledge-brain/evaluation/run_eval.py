"""Run the Knowledge Brain evaluation set against a running local API.

Usage: python -m evaluation.run_eval --base-url http://127.0.0.1:8000
Results are written to evaluation/results.csv. Review expected behavior manually before
using the output as a score; starter labels are not yet ground-truth validated.
"""
import argparse
import csv
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--cases", default=str(ROOT / "cases.json"))
    parser.add_argument("--output", default=str(ROOT / "results.csv"))
    args = parser.parse_args()

    data = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    rows = []
    for case in data["cases"]:
        started = time.perf_counter()
        try:
            response = requests.post(
                args.base_url.rstrip("/") + "/query",
                json={"question": case["question"], "top_k": 6},
                timeout=90,
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            body = response.json()
            rows.append({
                "case_id": case["case_id"],
                "category": case["category"],
                "expected_behavior": case["expected_behavior"],
                "http_status": response.status_code,
                "actual_status": body.get("status", "error"),
                "model": body.get("model", ""),
                "source_count": len(body.get("sources", [])),
                "needs_human": body.get("needs_human", ""),
                "input_tokens": (body.get("usage") or {}).get("input_tokens", ""),
                "output_tokens": (body.get("usage") or {}).get("output_tokens", ""),
                "estimated_cost_usd": body.get("estimated_cost_usd", ""),
                "latency_ms": latency_ms,
                "passed": "pending_manual_review",
                "failure_reason": body.get("detail", ""),
                "reviewed": case.get("reviewed", False),
            })
        except Exception as exc:
            rows.append({
                "case_id": case["case_id"],
                "category": case["category"],
                "expected_behavior": case["expected_behavior"],
                "http_status": "",
                "actual_status": "request_failed",
                "model": "",
                "source_count": 0,
                "needs_human": "",
                "input_tokens": "",
                "output_tokens": "",
                "estimated_cost_usd": "",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "passed": "no",
                "failure_reason": f"{type(exc).__name__}: {exc}",
                "reviewed": case.get("reviewed", False),
            })

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Evaluated {len(rows)} cases; results saved to {output}")
    print("Do not report an accuracy score until expected behaviors and each output are reviewed.")


if __name__ == "__main__":
    main()
