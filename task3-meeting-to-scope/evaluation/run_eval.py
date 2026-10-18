
import json
import sys
import time
from pathlib import Path

from evaluation.checks import evaluate_behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.agents import generate_package

CASES_FILE = PROJECT_ROOT / "evaluation" / "cases.json"
REPORT_FILE = PROJECT_ROOT / "evaluation" / "report.json"


def evaluate_case(case):
    case_id = case["case_id"]
    start = time.perf_counter()

    try:
        package = generate_package(
            client_name="Evaluation Client",
            project_name=f"Evaluation {case_id}",
            transcript=case["transcript"],
        )

        requirements = package.get("requirements", [])
        questions = package.get("open_questions", [])

        # Temporary structural check only.
        # Semantic checks will be added in the next step.
        result = evaluate_behavior(case, package)

        return {
            **result,
            "category": case.get("category"),
            "requirement_count": len(requirements)
            if isinstance(requirements, list) else None,
            "open_question_count": len(questions)
            if isinstance(questions, list) else None,
            "latency_seconds": round(time.perf_counter() - start, 2),
            "error": None,
        }

    except Exception as exc:
        message = str(exc)
        is_rate_limit = (
            "429" in message
            or "rate limit" in message.lower()
            or "ratelimit" in type(exc).__name__.lower()
        )

        return {
            "case_id": case_id,
            "category": case.get("category"),
            "expected_behavior": case.get("expected_behavior"),
            "status": "error",
            "error_type": (
                "rate_limit" if is_rate_limit
                else type(exc).__name__
            ),
            "latency_seconds": round(time.perf_counter() - start, 2),
            "error": message,
        }


def main():
    with CASES_FILE.open("r", encoding="utf-8") as file:
        cases = json.load(file)["cases"]

    results = []

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] Running {case['case_id']}...")
        result = evaluate_case(case)
        results.append(result)

        print(
            f"  Status: {result['status']}"
            + (
                f" ({result['error_type']})"
                if result.get("error_type") else ""
            )
        )

        # Stop when quota is exhausted instead of wasting more calls.
        if result.get("error_type") == "rate_limit":
            print("Rate limit detected. Stopping this run.")
            break

    passed = sum(r["status"] == "passed" for r in results)
    failed = sum(r["status"] == "failed" for r in results)
    errors = sum(r["status"] == "error" for r in results)

    report = {
        "total_cases": len(cases),
        "attempted": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "not_run": len(cases) - len(results),
        "structural_pass_rate_percent": round(
            passed / len(results) * 100, 2
        ) if results else 0,
        "results": results,
        "note": (
            "Structural checks only; this is not yet a semantic "
            "evaluation of expected_behavior."
        ),
    }

    with REPORT_FILE.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("\nEvaluation summary")
    print("------------------")
    print(f"Total cases: {len(cases)}")
    print(f"Attempted:   {len(results)}")
    print(f"Passed:      {passed}")
    print(f"Failed:      {failed}")
    print(f"Errors:      {errors}")
    print(f"Not run:     {report['not_run']}")
    print(f"Report:      {REPORT_FILE}")


if __name__ == "__main__":
    main()
