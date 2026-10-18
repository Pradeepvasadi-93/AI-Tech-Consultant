import argparse, csv, json, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
SAMPLE_A = ROOT.parent / "data" / "sample_transcripts" / "meeting_a.json"

def request_json(method, url, **kwargs):
    response = requests.request(method, url, timeout=180, **kwargs)
    response.raise_for_status()
    return response.json()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--cases", default=str(ROOT / "cases.json"))
    parser.add_argument("--output", default=str(ROOT / "results.csv"))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    rows = []
    for case in cases:
        started = time.perf_counter()
        row = {
            "case_id": case["case_id"], "category": case["category"],
            "expected_behavior": case["expected_behavior"], "http_status": "",
            "actual_status": "", "requirements_count": "", "open_questions_count": "",
            "estimates_count": "", "feasibility_unverified_count": "",
            "proposal_generated": "", "change_added": "", "change_modified": "",
            "change_removed": "", "latency_ms": "", "passed": "pending_manual_review",
            "failure_reason": ""
        }
        try:
            if case["category"] == "follow_up":
                seed = json.loads(SAMPLE_A.read_text(encoding="utf-8"))
                created = request_json("POST", base + "/projects", json={
                    "client_name": seed["client_name"], "project_name": seed["project_name"],
                    "transcript": case.get("baseline_transcript", seed["transcript"]), "meeting_id": "evaluation-baseline"
                })
                pid = created["project_id"]
                request_json("POST", f"{base}/projects/{pid}/approve", json={
                    "version": created["version"], "reviewer": "evaluation-runner",
                    "notes": "Establish baseline for evaluation only"
                })
                result = request_json("POST", f"{base}/projects/{pid}/meetings/follow-up", json={
                    "transcript": case["transcript"], "meeting_id": case["case_id"]
                })
                row["http_status"] = 200
                package = result.get("package", {})
                change = result.get("change_report", {})
                row["actual_status"] = result.get("status", "unknown")
                row["change_added"] = change.get("counts", {}).get("added", 0)
                row["change_modified"] = change.get("counts", {}).get("modified", 0)
                row["change_removed"] = change.get("counts", {}).get("removed", 0)
            else:
                result = request_json("POST", base + "/projects", json={
                    "client_name": "Evaluation Client", "project_name": case["case_id"],
                    "transcript": case["transcript"], "meeting_id": case["case_id"]
                })
                row["http_status"] = 201
                package = result.get("package", {})
                row["actual_status"] = result.get("status", "unknown")
            row["requirements_count"] = len(package.get("requirements", []))
            row["open_questions_count"] = len(package.get("open_questions", []))
            row["estimates_count"] = len(package.get("estimates", []))
            row["feasibility_unverified_count"] = sum(
                1 for f in package.get("feasibility", []) if f.get("status") == "unverified"
            )
            row["proposal_generated"] = bool(package.get("proposal_markdown"))
        except Exception as exc:
            row["actual_status"] = "request_failed"
            row["passed"] = "no"
            response = getattr(exc, "response", None)
            row["http_status"] = response.status_code if response is not None else ""
            row["failure_reason"] = (
                f"HTTP {response.status_code}: {response.text[:500]}"
                if response is not None else f"{type(exc).__name__}: {exc}"
            )
        row["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        rows.append(row)
        print(f"{case['case_id']}: {row['actual_status']} ({row['latency_ms']} ms)")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Executed {len(rows)} evaluation cases; results saved to {output}")
    print("passed remains pending_manual_review until each result is compared with expected_behavior.")
if __name__ == "__main__":
    main()
