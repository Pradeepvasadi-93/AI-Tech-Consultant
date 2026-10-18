# AI_LOG — AI Tech Consultant

## 1. Purpose

This log documents AI-assisted development practices, recorded design decisions and known verification gaps. Update it when meaningful code or prompt changes are accepted. Do not invent tool calls, measurements, code changes or test results.

## 2. Areas where AI assistance was used

Project context indicates AI assistance was used to support:
- architecture and agent responsibility explanations
- Python/FastAPI/LangGraph workflow implementation and review
- troubleshooting imports, environment configuration and service integration
- structured output and follow-up scope comparison design
- evaluation case/test planning and documentation
- analysis of failure reports and proposed fixes

The developer remains responsible for reviewing code, running tests, checking security and confirming compliance with the assignment rubric.

## 3. Recorded decisions and verification

| Area | Recorded decision/observation | Verification required |
|---|---|---|
| Shared knowledge | Task 1 is intended as the retrieval service for downstream agents | Verify Task 2 and Task 3 call the actual API and handle outages |
| Task 3 orchestration | LangGraph stages have distinct responsibilities | Inspect graph and stage outputs |
| Task 3 API | FastAPI service; reported port `8003` | Verify actual entry point and config |
| Task 1 API | Reported port `8000` | Verify config and health behavior |
| Scope baseline | Follow-up compares against approved baseline | Test approval state transitions and baseline preservation |
| Requirement merge | Preserve baseline and add unmatched requirements; do not auto-remove items | Test removals and semantically modified titles |
| Estimates | Calculate totals deterministically in Python | Test arithmetic and review task assumptions |
| Observability | Task 3 notes reference Logfire spans | Verify useful traces without secrets |
| Evaluation | Distinguish heuristic checks from semantic review | Inspect raw outputs and expected outcomes |

## 4. Review policy for AI-generated changes

For each material AI-assisted change:
1. Review the diff before accepting it.
2. Check imports, types, error handling and dependency compatibility.
3. Run relevant unit and integration tests.
4. Add a regression test for every fixed defect.
5. Inspect generated output for semantic correctness, not only valid JSON or field presence.
6. Ensure credentials and confidential customer data are not committed.
7. Record actual test results below.

AI-generated output is a draft, not proof that code works or that a security control is effective.

## 5. Known issues and actions

### Task 1 — Knowledge Brain
- Available evaluation report says KB-020 returned `answered` when `must_escalate` was expected.
- Many routine cases returned `needs_human`; these need individual review for over-escalation versus appropriate abstention.
- Estimated-cost fields were blank in the available CSV.
- Citation correctness was not fully validated.

**Action:** fix and regression-test KB-020, review outputs, improve cost logging and measure citation support.

### Task 2 — Inbox Agent
- 20/20 classification result applies only to a hand-authored dataset.
- Classification accuracy does not establish draft quality.
- The 20-consecutive-unchanged-draft autonomy rule needs verification in implementation and audit history.
- Simulated sends must be distinguished from actual email-provider sends.

**Action:** verify counter persistence/reset rules, server-side send gate, approval workflow and audit records; expand evaluation as required.

### Task 3 — Meeting-to-Scope
- Developer reports 20 evaluation cases passing and four unit tests passing; the final evaluation artifact was not independently inspected for this consolidated documentation.
- Some evaluation checks are heuristic.
- Baseline merge preserves requirements and appends unmatched requirements; explicit removals require review.
- Measured model accuracy, latency and cost comparison has not been supplied.

**Action:** attach raw evaluation output, inspect additions/modifications/removals and out-of-scope detection, and benchmark candidates on identical cases.

### Assignment model requirement
Prior notes indicate the assignment may require Claude as the central model. Confirm the original rubric; do not claim compliance based only on the current Groq configuration.

## 6. Evaluation integrity rules

- Never fabricate accuracy, latency, tokens, cost, citations or test results.
- Mark unexecuted tests as pending.
- Report dataset size and conditions beside every score.
- Distinguish HTTP success from semantic correctness.
- Separate provider errors/rate limits from behavior failures.
- Keep failed cases in the report.
- Use identical cases/settings for model comparison.
- Label results as measured, developer-reported, heuristic or manually reviewed.

## 7. Change log

The entries below summarize context available during documentation preparation, not a complete Git history. Replace approximate dates with actual commit dates where available.

| Date/period | Area | Change or observation | Evidence/status |
|---|---|---|---|
| Development period; exact date not recorded | Task 1 ingestion | Sitemap parsing, HTML parsing, crawler manifest/checkpoint and image processing were discussed/implemented | Verify current source and tests |
| Development period; exact date not recorded | Task 1 retrieval | Qdrant retrieval and embedding-based query workflow were discussed | Verify current API and retrieval tests |
| Development period; exact date not recorded | Task 2 | Rule-based email classification and draft/review workflow evaluated | Available report says 20/20 classifier cases and 11 tests passed |
| Development period; exact date not recorded | Task 3 | LangGraph roles, feasibility query, scope, estimates and proposal review implemented | Developer reports workflow working |
| Development period; exact date not recorded | Task 3 follow-up | Baseline requirements passed into follow-up generation; merge logic preserves baseline and appends new requirements | Validate current code and regression cases |
| 2026-10-18 | Documentation | Project-wide README, design, evaluation and AI usage log prepared from existing task documentation and evaluation notes | Update after repository-level verification |

## 8. Entry template

Append one entry for each significant AI-assisted change:

```markdown
### YYYY-MM-DD — Short change title
- **Problem:**
- **AI assistance used for:**
- **Human changes/review:**
- **Files changed:**
- **Tests run:**
- **Actual results:**
- **Known limitations:**
- **Follow-up action:**
```

## 9. Declaration

This log summarizes AI-assisted development practices and known verification gaps from the available project context. It does not claim that every suggestion was accepted, every test was rerun, or every generated output was correct. The final source code, test logs, evaluation artifacts and Git history remain the authoritative implementation evidence.
