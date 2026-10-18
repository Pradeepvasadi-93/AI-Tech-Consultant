# AI Log — Task 3

- LangGraph orchestrates five roles: Transcript Analyst, Product Feasibility, Scope Agent, Estimation Agent, and Proposal/Review Agent.
- Groq-hosted LLM calls are made through `langchain-groq`; `GROQ_MODEL` and `GROQ_API_KEY` are environment-configurable.
- Deterministic Python handles SQLite persistence, versioning, approval gates, audit events, duplicate simulated-send prevention, and change comparison.
- Product feasibility reuses Task 1 Knowledge Brain via its `/query` endpoint.
- Long transcripts are chunked; extracted records retain short source excerpts for reviewer traceability.
- Human approval remains mandatory before simulated proposal delivery. Outputs are drafts, not commitments.
\n- Added optional Logfire observability: FastAPI request instrumentation plus named spans for LangGraph nodes, Groq JSON calls, Task 1 knowledge queries, and package generation. Sensitive transcript/prompt contents are not recorded as span attributes. Cloud export is opt-in via `LOGFIRE_TOKEN`; local console tracing is configurable.\n