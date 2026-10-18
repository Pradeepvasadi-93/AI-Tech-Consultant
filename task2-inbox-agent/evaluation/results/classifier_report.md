# Task 2 Classifier Evaluation Report

- Dataset cases: **20**
- Correct classifications: **20/20**
- Incorrect classifications: **0/20**
- Category accuracy: **100.0%**
- Mean classifier latency: **0.0202 ms**
- p95 classifier latency: **0.0297 ms**
- Classifier model cost: **$0.00** (rule-based; no LLM call)

## Confusion Matrix

| Expected / Actual | complaint | follow_up | how_to | project_request | quote_request | refund_cancellation | troubleshooting |
|---|---|---|---|---|---|---|---|
| complaint | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| follow_up | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| how_to | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| project_request | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| quote_request | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| refund_cancellation | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| troubleshooting | 0 | 0 | 0 | 0 | 0 | 0 | 3 |

## Failed Cases

No category classification failures.

## Limitations

This report measures only the deterministic classifier against hand-authored cases. It does not measure risk or urgency accuracy, human-review decisions, draft quality, evidence grounding, or Knowledge Brain retrieval. Evaluate a second model/configuration on the same cases separately if required by the assignment.
