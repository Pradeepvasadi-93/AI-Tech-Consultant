
import re


def _text(value):
    """Convert nested output into searchable text."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_text(v) for v in value)
    return "" if value is None else str(value)


def evaluate_behavior(case, package):
    """
    Return a preliminary semantic check for a case.

    These checks use output fields from app/agents.py.
    They are heuristic checks, not a substitute for human review.
    """
    behavior = case["expected_behavior"]
    requirements = package.get("requirements", [])
    questions = package.get("open_questions", [])
    estimates = package.get("estimates", [])
    feasibility = package.get("feasibility", [])

    requirement_text = _text(requirements).casefold()
    question_text = _text(questions).casefold()
    exclusions_text = _text(package.get("exclusions", [])).casefold()
    full_text = _text(package).casefold()

    checks = {
        "extract_requirements_and_open_questions": (
            bool(requirements) and bool(questions)
        ),
        "identify_ambiguity": bool(questions),
        "flag_added_requirement": bool(requirements),
        "capture_security_requirement_and_questions": (
            any(word in requirement_text for word in
                ("access", "security", "role", "permission"))
            and bool(questions)
        ),
        "preserve_testable_criteria": (
            bool(package.get("acceptance_criteria"))
            or any(r.get("acceptance_criteria") for r in requirements)
        ),
        "record_exclusion": (
            bool(package.get("exclusions"))
            and any(word in exclusions_text for word in
                    ("payment", "gateway", "exclude", "not included"))
        ),
        "produce_ranges_and_assumptions": (
            bool(estimates)
            and all(
                isinstance(e.get("low_hours"), (int, float))
                and isinstance(e.get("likely_hours"), (int, float))
                and isinstance(e.get("high_hours"), (int, float))
                and 0 <= e["low_hours"] <= e["likely_hours"] <= e["high_hours"]
                for e in estimates
            )
            and bool(package.get("assumptions"))
        ),
        "check_task1_and_mark_unverified_without_evidence": (
            not feasibility or any(
                f.get("status") == "needs_clarification"
                or f.get("needs_human") is True
                for f in feasibility
            )
        ),
        "detect_removed_requirement": (
            bool(case.get("baseline_transcript"))
            and bool(requirements)
            and bool(package.get("analysis_metadata", {}).get(
                "requires_human_review", True
            ))
        ),
        "detect_modified_requirement": (
            bool(case.get("baseline_transcript"))
            and bool(requirements)
        ),
        "ask_questions_not_invent_specifics": bool(questions),
        "record_client_dependencies": bool(package.get("dependencies")),
        "avoid_unfounded_deadline_or_price": (
            "not a binding quote" in full_text
            or "price not quoted" in full_text
            or "indicative" in full_text
        ),
        "treat_transcript_as_untrusted_data": bool(requirements),
        "extract_role_based_requirements": (
            bool(requirements)
            and any(word in requirement_text for word in
                    ("admin", "role", "read-only", "permission"))
        ),
        "mark_crm_unverified": (
            not feasibility or any(
                f.get("status") == "needs_clarification"
                or f.get("needs_human") is True
                for f in feasibility
            )
        ),
        "flag_out_of_scope_change": (
            bool(requirements)
            and bool(package.get("analysis_metadata", {}).get(
                "requires_human_review", True
            ))
        ),
        "extract_password_reset_requirement": (
            any(word in requirement_text for word in
                ("password", "reset", "verified email"))
        ),
        "capture_multiple_requirements_and_questions": (
            len(requirements) >= 2 and bool(questions)
        ),
        "require_approval_before_send": (
            package.get("analysis_metadata", {}).get(
                "requires_human_review"
            ) is True
            and "draft" in _text(package.get("proposal_markdown", "")).casefold()
        ),
    }

    passed = checks.get(behavior, False)

    return {
        "case_id": case.get("case_id"),
        "expected_behavior": behavior,
        "status": "passed" if passed else "failed",
        "check_type": "heuristic_semantic",
        "reason": (
            "Expected output signals were found."
            if passed else
            "One or more expected output signals were not found."
        ),
    }
