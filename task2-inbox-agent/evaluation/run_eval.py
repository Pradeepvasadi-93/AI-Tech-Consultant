
"""Run a deterministic classifier evaluation and write results."""
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.schemas import EmailRequest
from app.email.classifier import classify_email

DATA_PATH = ROOT / "data" / "eval_cases.json"
OUT_DIR = ROOT / "evaluation" / "results"


def main():
    cases = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    if not cases:
        raise ValueError("Evaluation dataset is empty.")

    rows = []
    correct = 0
    latencies = []

    for case in cases:
        email = EmailRequest(
            sender=case["sender"],
            subject=case["subject"],
            body=case["body"],
            conversation_context=case.get("conversation_context", ""),
        )

        started = time.perf_counter()
        result = classify_email(email)
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)

        expected = case["expected_category"]
        actual = result.category.value
        passed = actual == expected
        correct += int(passed)

        rows.append({
            "case_id": case.get("id", ""),
            "subject": case["subject"],
            "expected_category": expected,
            "actual_category": actual,
            "pass": passed,
            "latency_ms": round(latency_ms, 4),
        })

    total = len(cases)
    accuracy = correct / total
    sorted_latencies = sorted(latencies)
    p95_index = max(0, min(total - 1, int(0.95 * total) - 1))

    # Build a confusion matrix: expected category vs actual category.
    categories = sorted({
        row["expected_category"] for row in rows
    } | {
        row["actual_category"] for row in rows
    })

    confusion = {
        expected: {actual: 0 for actual in categories}
        for expected in categories
    }

    for row in rows:
        confusion[row["expected_category"]][row["actual_category"]] += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUT_DIR / "classifier_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    metrics = {
        "evaluation_name": "Task 2 Inbox Agent rule-based classifier",
        "dataset": str(DATA_PATH.relative_to(ROOT)),
        "case_count": total,
        "correct_categories": correct,
        "incorrect_categories": total - correct,
        "category_accuracy": round(accuracy, 4),
        "mean_classifier_latency_ms": round(sum(latencies) / total, 4),
        "p95_classifier_latency_ms": round(
            sorted_latencies[p95_index], 4
        ),
        "model_cost_usd": 0.0,
        "confusion_matrix": confusion,
        "notes": [
            "This evaluation measures category classification only.",
            "Risk, urgency, and human-review accuracy are not measured "
            "because the dataset does not define expected values for them.",
            "Cost is zero for this rule-based classifier because it does "
            "not call an LLM.",
            "Latency is local runtime and varies by machine.",
            "These are hand-authored cases; results do not guarantee "
            "real-world accuracy.",
            "A separate comparison using the same cases is needed to "
            "evaluate a second model or configuration.",
        ],
        "results": rows,
    }

    metrics_path = OUT_DIR / "classifier_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    report = [
        "# Task 2 Classifier Evaluation Report",
        "",
        f"- Dataset cases: **{total}**",
        f"- Correct classifications: **{correct}/{total}**",
        f"- Incorrect classifications: **{total - correct}/{total}**",
        f"- Category accuracy: **{accuracy:.1%}**",
        f"- Mean classifier latency: **{metrics['mean_classifier_latency_ms']:.4f} ms**",
        f"- p95 classifier latency: **{metrics['p95_classifier_latency_ms']:.4f} ms**",
        "- Classifier model cost: **$0.00** (rule-based; no LLM call)",
        "",
        "## Confusion Matrix",
        "",
        "| Expected / Actual | " + " | ".join(categories) + " |",
        "|---|" + "---|" * len(categories),
    ]

    for expected in categories:
        values = [
            str(confusion[expected][actual])
            for actual in categories
        ]
        report.append("| " + expected + " | " + " | ".join(values) + " |")

    report.extend([
        "",
        "## Failed Cases",
        "",
    ])

    failures = [row for row in rows if not row["pass"]]

    if failures:
        for row in failures:
            report.append(
                f"- **{row['case_id']}** ({row['subject']}): "
                f"expected `{row['expected_category']}`, "
                f"predicted `{row['actual_category']}`."
            )
    else:
        report.append("No category classification failures.")

    report.extend([
        "",
        "## Limitations",
        "",
        "This report measures only the deterministic classifier against "
        "hand-authored cases. It does not measure risk or urgency accuracy, "
        "human-review decisions, draft quality, evidence grounding, or "
        "Knowledge Brain retrieval. Evaluate a second model/configuration "
        "on the same cases separately if required by the assignment.",
        "",
    ])

    report_path = OUT_DIR / "classifier_report.md"
    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"Evaluated {total} cases")
    print(f"Category accuracy: {accuracy:.1%} ({correct}/{total})")
    print(f"Mean latency: {metrics['mean_classifier_latency_ms']:.4f} ms")
    print(f"p95 latency: {metrics['p95_classifier_latency_ms']:.4f} ms")
    print(f"CSV results: {csv_path}")
    print(f"JSON metrics: {metrics_path}")
    print(f"Markdown report: {report_path}")


if __name__ == "__main__":
    main()
