# DESIGN — AI Tech Consultant

## 1. Design goals

The project combines three applications around a shared Knowledge Brain. Design priorities are evidence-grounded output, explicit uncertainty, human control of consequential actions, traceability, reproducibility and visible failures.

1. One shared knowledge service instead of duplicated product knowledge.
2. Structured, validated data between agent stages.
3. Source-grounded claims and abstention when evidence is insufficient.
4. Human approval before customer messages or scope changes become commitments.
5. Traceability for inputs, outputs, decisions, versions and evaluation runs.
6. Safe failure on timeouts, rate limits, invalid model output and missing evidence.
7. Independently testable components and workflows.

## 2. Logical architecture

```text
Sources -> ingestion/parsing -> chunks + embeddings -> vector store
                                                   |
                                            Task 1 API
                                             /       \\
                                      Task 2           Task 3
                                   email -> draft   transcript -> scope
                                   -> review        -> estimates -> proposal
                                             \\       /
                                          human approval
                                          audit/versioning
```

This is a logical architecture; verify the final deployment topology, databases and frontend from the actual repository.

## 3. Task 1 — Knowledge Brain

### Ingestion path
1. Discover source URLs from configured sitemaps or source lists.
2. Fetch with bounded timeouts and error handling.
3. Parse and normalize content.
4. Process supported images/documents using configured processors.
5. Chunk content and retain source metadata.
6. Generate embeddings and upsert into the vector store.
7. Track processing state in a manifest/checkpoint for incremental runs.
8. Define update/delete behavior so stale content is not retrieved.

Prior Task 1 work references sitemap parsing, BeautifulSoup, `ingestion/manifest.json`, image processing, embeddings and Qdrant. Confirm current supported formats and deletion semantics in code.

### Query path
Validate question -> embed query -> retrieve evidence -> generate grounded answer or escalate -> return source references/status -> record safe operational metadata. A retrieved source is not necessarily supporting evidence; citation relevance must be evaluated.

## 4. Task 2 — Inbox Agent

1. Validate incoming email.
2. Classify its category and identify urgency/sensitive actions.
3. Query Task 1 for relevant evidence.
4. Generate a reply grounded in retrieved evidence.
5. Show the email, evidence and draft to a reviewer.
6. Record approval/rejection/edits and reviewer metadata.
7. Send only after approval unless a separately validated autonomy policy is explicitly enabled.

The assignment notes refer to 20 consecutive unchanged drafts before autonomous sending. Verify the persisted counter, reset rules, excluded categories, behavior after prompt/model changes, and server-side send gate. Tests must distinguish simulated sends from real provider sends.

## 5. Task 3 — Meeting-to-Scope

| Role | Responsibility | Output |
|---|---|---|
| Transcript Analyst | Extract requirements, decisions, constraints, assumptions, commitments and questions | Structured analysis |
| Product Feasibility | Query Task 1 and identify evidence or uncertainty | Feasibility finding/review flag |
| Scope Agent | Define deliverables, exclusions, dependencies and acceptance criteria | Structured scope |
| Estimation Agent | Estimate low/likely/high hours per task | Estimates and assumptions |
| Proposal/Review Agent | Check consistency and prepare a client-facing draft | Proposal draft and review flags |

Task 3 documentation describes FastAPI, LangGraph, Groq and Logfire. Reported local ports are Task 1 `8000` and Task 3 `8003`.

### Follow-up handling
1. Load the approved baseline.
2. Extract the follow-up transcript.
3. Match requirements using stable IDs or a documented strategy.
4. Detect additions, modifications, explicit removal requests and unresolved conflicts.
5. Re-estimate affected work.
6. Flag potential out-of-scope requests.
7. Save a new draft revision.
8. Keep the approved version unchanged until the new version is approved.

The described merge logic preserves baseline requirements and appends unmatched requirements; it does not automatically remove baseline items. Title-based matching can miss semantic changes, so change reports require review.

## 6. Recommended data records

| Record | Useful fields |
|---|---|
| Knowledge source | ID, URL/path, hash, fetched time, status |
| Knowledge chunk | ID, source ID, text, metadata, embedding reference |
| Email case | ID, category, evidence, draft version, approval, feedback, send audit |
| Scope project | ID, client/project, transcript references, approved baseline, current draft |
| Requirement | Stable ID, description, status, priority, source passage, acceptance criteria |
| Estimate item | Task, low/likely/high hours, rationale, assumptions, reviewer status |
| Proposal version | Scope/estimate version, artifact, approval state, reviewer, timestamp |
| Evaluation run | Dataset/version, model/config, date, case result, latency, tokens, cost, errors |

These are recommendations, not a claim that all records already exist in persistence.

## 7. Reliability and error handling

- Use timeouts and bounded retries with backoff.
- Separate provider errors from behavioral failures.
- Return structured errors with request IDs.
- Do not convert dependency failures into fabricated or empty answers.
- Validate model output before storing or acting on it.
- Make state-changing operations idempotent where practical.
- Expose health checks separately from business endpoints.
- Log useful metrics without secrets or unnecessary transcript content.

## 8. Security and privacy

- Treat retrieved content, emails, pages and transcripts as untrusted data.
- Instructions inside source material must not override system rules or approval controls.
- Keep credentials in environment variables/secrets management, never Git.
- Limit payload sizes and validate uploads.
- Restrict access to customer records and approval endpoints.
- Minimize personal data in logs.
- Require authorization for external messages and scope approvals.
- Maintain an audit trail for approvals, prompts and model changes.

## 9. Observability and tests

Task 3 notes reference Logfire spans around LangGraph stages. The integrated project should record request IDs, stage duration, retrieval/model outcomes, retries, provider errors, reviewer decisions and evaluation IDs.

Test layers:
- Unit: parsers, matching, totals, validators and state transitions.
- Integration: API schemas, retrieval, persistence and service calls.
- Workflow: initial scope, approvals, follow-up changes, email review and escalation.
- Safety: prompt injection, unsupported claims, unauthorized sends and baseline preservation.
- Evaluation: fixed datasets and case-level expected outcomes.
- Operations: timeouts, rate limits, unavailable dependencies, malformed output and recovery.

## 10. Known design risks

- Retrieved evidence may not support generated claims.
- Over-escalation harms usability; under-escalation can be unsafe.
- Heuristic checks may pass semantically wrong outputs.
- Title-based matching may miss requirement modifications.
- Mentioning approval in text is insufficient unless API transitions enforce it.
- Confirm the required central model against the original assignment rubric.
