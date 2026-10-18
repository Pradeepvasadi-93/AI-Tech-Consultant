# AI Tech Consultant — Task 1: Knowledge Brain

A Python service that ingests Brilliant Directories support articles and screenshots, indexes searchable chunks in Qdrant, answers questions using retrieved evidence and Claude, and escalates questions that cannot be answered safely.

## Architecture

`Sitemap → resumable crawler → normalized article JSON → chunker → embeddings → Qdrant → retrieval → Claude answer with citations / human escalation`

Task 2 (Inbox Agent) and Task 3 (Meeting to Scope) should call this service through its API. They must not duplicate its crawler, embeddings, or retrieval implementation.

## Requirements

- Python 3.11 or 3.12 recommended
- Qdrant Cloud collection or a compatible Qdrant endpoint
- Anthropic API key for grounded answer generation
- Gemini API key for Gemini embeddings, or enough local disk/RAM to load the `sentence-transformers/all-mpnet-base-v2` fallback
- OpenAI API key only when image descriptions are enabled

## Setup

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and provide `QDRANT_URI`, `QDRANT_API_KEY`, and `ANTHROPIC_API_KEY`. For image descriptions, set `OPENAI_API_KEY`. Do not commit `.env` or share its values. Set `KNOWLEDGE_API_KEY` in deployments; if set, protected endpoints require the `X-API-Key` header.

## Run the API

From this directory:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

### Main endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/query` | Grounded answer with source citations or escalation |
| `POST` | `/ingestion/run` | Queue a full sitemap sync |
| `GET` | `/ingestion/status` | Latest job and manifest counts |
| `POST` | `/escalations` | Create an escalation |
| `GET` | `/escalations` | List escalations |
| `GET` | `/escalations/{id}` | Read one escalation |
| `POST` | `/escalations/{id}/resolve` | Approve and index a human answer |

Example query:

```bash
curl -X POST http://127.0.0.1:8000/query ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"How do I configure my website logo?\",\"top_k\":6}"
```

If `KNOWLEDGE_API_KEY` is set, include `-H "X-API-Key: YOUR_KEY"`.

## Run ingestion

Small smoke test (first 3 sitemap URLs; no image model calls):

```bash
python test_api.py
```

For a controlled CLI run with images disabled:

```bash
python -m rag.pipeline --url https://support.brilliantdirectories.com/support/sitemap.xml --mode sitemap --limit 10 --delay 1 --skip-images
```

Full daily sync:

```bash
python -m rag.pipeline --url https://support.brilliantdirectories.com/support/sitemap.xml --mode sitemap --delay 1
```

A daily scheduler is also available:

```bash
python scheduler.py
```

It runs at 02:00 UTC. Run only one scheduler instance. In production, a managed scheduler/cron job is generally easier to monitor.

## Tests and evaluations

```bash
pytest -q tests
```

The unit tests do not call external services. The API integration needs valid Qdrant/model credentials:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m evaluation.run_eval
```

The starter evaluation set has 20 cases. Its expected behaviors require human/source review before publishing accuracy numbers. The evaluation runner records status, source count and latency; reviewers must verify factual correctness and citation support. Never report scores that were not actually measured.

## Data and checkpoints

- `ingestion/documents/`: normalized page JSON and image descriptions
- `ingestion/manifest.json`: created automatically on first crawl; stores crawl status, attempts, hashes, validators and indexing checkpoints
- `chunking/output/`: persisted chunks
- `embeddings/output/`: persisted embedding records (these files can be large)
- `data/escalations.sqlite3`: escalation and ingestion-job records
- Qdrant: searchable vectors and metadata

Manifest paths are anchored to this project directory, not the process's current working directory. Corrupt manifests raise an explicit error instead of being silently overwritten.

## Important limitations to validate before production

- The starter evaluation labels are hypotheses until reviewed against current support articles.
- Qdrant, Claude, embedding-provider and image-provider calls require configured credentials and live connectivity.
- Image processing failures are recorded per image and do not stop article ingestion; review failures and retry them.
- Enable API-key protection in deployed environments and use HTTPS, least-privilege credentials, request limits, and monitoring.
- Human-approved answers are indexed in Qdrant, but they should be periodically reviewed and versioned as product knowledge changes.
