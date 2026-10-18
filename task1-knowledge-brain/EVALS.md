# Task 1 Evaluation Notes

## Automated unit tests

Last local run in the editing environment: **11 passed**.

Coverage includes:
- Chunking and title/source/image metadata.
- Manifest initialization, atomic writes and corrupt-manifest handling.
- Sitemap URL and `lastmod` parsing.
- Crawler checkpointing, unchanged-content skipping, changed-content refresh and transient HTTP retry.
- Health API contract.
- Escalation persistence and versioned approved-knowledge records.

These tests use local fixtures/mocks. They do not prove external service availability or the factual accuracy of generated answers.

## End-to-end evaluation

`evaluation/cases.json` contains 20 starter cases. Run:

```bash
python -m evaluation.run_eval --base-url http://127.0.0.1:8000
```

The runner writes `evaluation/results.csv` with HTTP status, API status, model, source count, latency, token usage and estimated cost when rates are configured. The starter expected behaviors are not yet human-validated against the current help center; therefore the runner intentionally does not calculate a pass rate.

For model comparison, run the identical frozen cases against each configured model, save separate CSVs, and compare human-reviewed answer/citation quality, latency, token usage, estimated cost and failures. Configure cost rates from current provider pricing; the software does not hard-code prices.

Before reporting a score:
1. Verify each expected behavior against a current source article or approved expert answer.
2. Review whether each citation supports the generated claim.
3. Review every unsupported-question case for appropriate abstention/escalation.
4. Run the same cases after changes and preserve failures.
5. Record model name/version, embedding model, configuration, latency and actual provider cost.

## External checks still required

The following were not run in the offline editing environment:
- Full 1,696-URL sitemap crawl.
- Qdrant Cloud collection/vector dimension compatibility.
- Live Claude query and citation correctness.
- Live OpenAI image-description calls.
- Full 20-case API evaluation against a populated vector store.
- Daily scheduler execution in the deployment environment.
