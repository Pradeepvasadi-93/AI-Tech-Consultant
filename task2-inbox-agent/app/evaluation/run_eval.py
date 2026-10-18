
import json
import sys
from collections import defaultdict
from pathlib import Path

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "data" / "eval_cases.json"
API_URL = "http://127.0.0.1:8001/emails/classify"


def load_cases():
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    if not isinstance(cases, list) or not cases:
        raise ValueError("The evaluation dataset must be a non-empty JSON list.")

    return cases


def run_evaluation():
    cases = load_cases()
    correct = 0
    failures = 0
    category_totals = defaultdict(int)
    category_correct = defaultdict(int)
    confusion = defaultdict(int)

    with httpx.Client(timeout=30.0) as client:
        for case in cases:
            email = {
                "sender": case["sender"],
                "subject": case["subject"],
                "body": case["body"],
                "conversation_context": case.get(
                    "conversation_context", ""
                ),
            }

            expected = case["expected_category"]

            try:
                response = client.post(API_URL, json=email)
                response.raise_for_status()
                result = response.json()

                predicted = result["category"]
                if isinstance(predicted, dict):
                    predicted = predicted.get("value")

                category_totals[expected] += 1
                confusion[(expected, predicted)] += 1

                if predicted == expected:
                    correct += 1
                    category_correct[expected] += 1
                    outcome = "PASS"
                else:
                    outcome = "FAIL"

                print(
                    f"[{outcome}] {case.get('id', 'unknown')} | "
                    f"expected={expected} | predicted={predicted}"
                )

            except (httpx.HTTPError, KeyError, ValueError) as exc:
                failures += 1
                print(
                    f"[ERROR] {case.get('id', 'unknown')}: {exc}"
                )

    evaluated = len(cases)
    successful_predictions = evaluated - failures
    accuracy = (
        correct / successful_predictions
        if successful_predictions else 0.0
    )

    print("\n--- Evaluation summary ---")
    print(f"Dataset cases: {evaluated}")
    print(f"Successful API predictions: {successful_predictions}")
    print(f"API or response failures: {failures}")
    print(f"Correct classifications: {correct}")
    print(f"Accuracy on successful predictions: {accuracy:.2%}")

    print("\n--- Per-category results ---")
    for category in sorted(category_totals):
        total = category_totals[category]
        matched = category_correct[category]
        print(
            f"{category}: {matched}/{total} "
            f"({matched / total:.2%})"
        )

    print("\n--- Misclassifications ---")
    mistakes = [
        (expected, predicted, count)
        for (expected, predicted), count in confusion.items()
        if expected != predicted
    ]

    if not mistakes:
        print("No misclassifications among successful predictions.")
    else:
        for expected, predicted, count in sorted(mistakes):
            print(
                f"Expected {expected}, predicted {predicted}: "
                f"{count} case(s)"
            )

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    run_evaluation()
