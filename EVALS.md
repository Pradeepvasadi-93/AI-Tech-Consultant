# EVALS — AI Tech Consultant

## 1. Purpose and reporting policy

This report consolidates available evaluation evidence for Task 1 (Knowledge Brain), Task 2 (Inbox Agent), and Task 3 (Meeting-to-Scope). It separates measured results from owner-reported results and pending work. Results apply only to the datasets and checks that were actually run; they are not proof of perfect real-world accuracy.

## 2. Evidence summary

| Task | Available evidence | Interpretation |
|---|---|---|
| Task 1 — Knowledge Brain | 20 cases attempted; all 20 API requests returned HTTP 200; 3 `answered`, 17 `needs_human` | API requests completed, but answer quality was not fully scored |
| Task 2 — Inbox Agent | 20/20 hand-authored category labels matched expected labels | 100% on this small dataset only |
| Task 2 — Automated tests | 11 tests reported passing | Rerun in final environment |
| Task 3 — Meeting-to-Scope | Developer reports 20 cases passed and four unit tests passed | Reported, not independently verified here; checks are described as heuristic |
| Model comparison | No paired measured results supplied | Accuracy, latency and cost comparison remains pending |

## 3. Task 1 — Knowledge Brain

**Dataset:** `task1-knowledge-brain/evaluation/cases.json`  
**Output referenced in previous report:** `task1-knowledge-brain/evaluation/results.csv`  
**Command reported:** `python -m evaluation.run_eval`  
**Model reported for that run:** `openai/gpt-oss-120b`

| Metric | Observed result | Meaning |
|---|---:|---|
| Cases attempted | 20 | All cases attempted |
| HTTP 200 | 20/20 (100%) | Request-level success, not answer accuracy |
| `answered` | 3/20 | KB-003, KB-010 and KB-020 |
| `needs_human` | 17/20 | All remaining cases |
| Expected answer-with-citations cases | 15 | Expected labels in the dataset |
| Answer-oriented cases returning `answered` | 2/15 | Status-only count; correctness not scored |
| Expected `must_escalate` cases | 5 | Expected labels in the dataset |
| Escalation cases returning `needs_human` | 4/5 | Status-only count |
| Estimated cost | Unavailable | `estimated_cost_usd` was blank |
| End-to-end request latency | Approximately 2.21–16.69 seconds | Measured around the HTTP request; not isolated model latency |

### Critical issue: KB-020

The available report says **KB-020 is security-sensitive and returned `answered` although `must_escalate` was expected**.

Required follow-up:
1. Inspect prompt, retrieved context and actual response.
2. Correct the unsafe answer/escalation behavior.
3. Add a regression test.
4. Rerun the full dataset and check for regressions.

Many routine cases returned `needs_human`. Review them individually to determine whether the system is correctly abstaining or over-escalating. A source count does not prove citations support the claims. The previous report notes that `passed` was initialized to `pending_manual_review`; manual review is required to score expected behavior.

**Conclusion:** the recorded run completed all 20 requests, but output quality and expected-behavior compliance were not fully scored. No final Task 1 accuracy percentage is claimed.

## 4. Task 2 — Inbox Agent

**Dataset:** `task2-inbox-agent/data/eval_cases.json`  
**Component evaluated:** deterministic/rule-based email classifier  
**Command reported:** `python -m evaluation.run_eval`

| Metric | Reported result | Interpretation |
|---|---:|---|
| Cases | 20 | Hand-authored evaluation dataset |
| Correct categories | 20/20 | All expected labels matched |
| Incorrect categories | 0/20 | No classification errors in this dataset |
| Category accuracy | 100.0% | Dataset-specific result only |
| Automated tests | 11 passed | Reported result; rerun before submission |

This does not prove generated replies are correct, grounded, safe, or ready to send. It does not prove the approval gate or the 20-consecutive-unchanged-draft autonomous-send rule is correctly implemented. Verify whether sending is simulated or performed by a real email provider.

Required verification:
1. Evaluate at least 50 realistic emails if required by the rubric.
2. Score draft grounding, completeness, tone and unsupported commitments.
3. Test approval, rejection, edits and feedback persistence.
4. Test missing evidence and Task 1 outage behavior.
5. Verify counter persistence, reset rules and server-side send enforcement.
6. Keep actual provider sends distinct from simulated sends in reports.

**Conclusion:** 100% classification accuracy is reported for 20 hand-authored cases, with 11 tests reported passing. This is a baseline, not a general quality guarantee.

## 5. Task 3 — Meeting-to-Scope

The project context identifies 20 cases (`SC-001`–`SC-020`) intended to cover requirement extraction, ambiguity, security/prompt injection, acceptance criteria, exclusions, estimates, feasibility, follow-up changes, dependencies, integrations, commercial safety and approval.

The developer reports all 20 cases working with 100% results. The actual final report and per-case generated outputs were not independently inspected when this consolidated report was prepared.

The developer previously reported this test result from the Task 3 root:

```text
python -m pytest -q
4 passed
```

Rerun before submission. The result is a prior report, not a fresh execution here.

### Follow-up change cases to retain

- A newly added requirement.
- A modified requirement.
- An explicit removal request.
- A request outside the approved baseline.
- An unresolved question.
- A follow-up with no actual changes.
- An attempt to override approval rules through transcript text.
- A Knowledge Brain timeout or missing evidence.

Verify the approved baseline remains unchanged until the revised scope is approved. Review the actual old/new requirements, not just whether a change-report field exists. The project notes state that some checks are heuristic, so field presence is not sufficient to establish semantic correctness.

**Conclusion:** Task 3's 20-case result and four passing tests are developer-reported. Attach the actual output report and manually review change classification before presenting the result as validated accuracy.

## 6. Model comparison — results pending

Candidates identified in project context:
- Configuration A: `openai/gpt-oss-120b`
- Configuration B: `openai/gpt-oss-20b`

No paired benchmark with measured accuracy, latency and cost was supplied. Expectations that the larger model may reason better and the smaller model may be faster/cheaper are hypotheses, not results. Do not declare a winner until both candidates are tested on identical cases.

**Rubric check:** prior project notes indicate the assignment may require Claude as the central model. Confirm the original assignment. If Claude is mandatory, include the required Claude configuration in the benchmark.

### Fair protocol

1. Freeze the same evaluation cases for both models.
2. Keep prompts, retrieval corpus, settings and baseline scope identical.
3. Run both models on all applicable cases.
4. Save raw output per case and report API errors separately.
5. Score correctness, evidence grounding, safety and change detection.
6. Record elapsed time and provider-reported tokens/cost.
7. Manually review safety-critical failures.
8. Do not count rate-limit or infrastructure errors as successful cases.

| Metric | GPT-OSS-120B | GPT-OSS-20B |
|---|---:|---:|
| Cases attempted | Pending | Pending |
| Cases passed under same rubric | Pending | Pending |
| Pass rate | Pending | Pending |
| Mean latency (seconds) | Pending | Pending |
| Median latency (seconds) | Pending | Pending |
| p95 latency (seconds) | Pending | Pending |
| Mean input tokens | Pending | Pending |
| Mean output tokens | Pending | Pending |
| Mean cost per case | Pending | Pending |
| Critical safety failures | Pending | Pending |

Calculate pass rate as `passed cases / cases actually evaluated × 100`. Report API errors and rate limits separately. Record exact model ID, date, prompt version and dataset version.

## 7. Cross-task metrics

| Dimension | Recommended measure |
|---|---|
| Answer quality | Human-scored factual correctness against a reference |
| Retrieval quality | Relevant-source recall/precision on labeled questions |
| Citation quality | Whether cited evidence supports the associated claim |
| Escalation | Correct escalation and unsafe-answer rates |
| Classification | Correct labels divided by evaluated emails |
| Draft quality | Grounding, completeness, policy compliance and edit rate |
| Requirement extraction | Reference requirement coverage and precision |
| Change detection | Correct additions/modifications/removals against approved baseline |
| Estimate quality | Error against engineer-reviewed reference ranges |
| Latency | Mean, median and p95 for identical workload |
| Cost | Actual provider usage cost per completed task |
| Reliability | Successful completions divided by attempts, with errors reported separately |
| Approval safety | Count of unauthorized external actions; target zero |

## 8. Reproducibility checklist

- [ ] Save the exact dataset version and raw case-level outputs.
- [ ] Record model ID, prompt version, settings and date.
- [ ] Record latency, token usage and cost where available.
- [ ] Separate provider errors from behavior failures.
- [ ] Manually review representative correct and incorrect outputs.
- [ ] Add regression tests for discovered failures.
- [ ] Rerun tests after fixes and preserve historical reports.
- [ ] Update this file with measured results only.

## 9. Overall conclusion

The evidence supports limited claims: Task 1 completed 20 API requests with HTTP 200 in the recorded run; Task 2's classifier matched 20/20 hand-authored labels and 11 tests were reported passing; Task 3's developer reports a 20-case result and four passing tests. These results are not directly comparable and do not establish a project-wide accuracy score.

Task 1's KB-020 security escalation miss needs attention. Task 2 draft quality and autonomous-send enforcement need separate evidence. Task 3 needs its final evaluation artifact and semantic review. Model comparison remains pending until both configurations are measured on the same cases.
