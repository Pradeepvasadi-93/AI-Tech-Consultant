# AI Tech Consultant — Frontend

A responsive React + Vite dashboard for the three local AI Tech Consultant services.

- **Task 1 — Knowledge Brain:** query grounded answers, display citations and cost/model metadata, view/resolve escalations, start ingestion, and inspect ingestion status.
- **Task 2 — Inbox Agent:** submit an email for classification/drafting, inspect inbox records, edit a proposed reply, record review decisions, submit feedback, and invoke the configured send/review route.
- **Task 3 — Meeting-to-Scope:** create a project from a transcript, inspect requirements/scope/estimates/proposal, approve a version, compare follow-up meetings, inspect version history/audit events, and call the service's proposal-delivery endpoint.

The UI does not invent a successful result: backend errors are displayed to the user. Proposal sending is labelled as a backend operation; the Task 3 service in the supplied source describes delivery as simulated-only.

## 1. Prerequisites

- Node.js 20 or newer (Node.js 18.18+ may work with the Vite version installed).
- npm.
- The three backend services running locally:
  - Task 1: `http://127.0.0.1:8000`
  - Task 2: `http://127.0.0.1:8001`
  - Task 3: `http://127.0.0.1:8002`

## 2. Install and run

Open PowerShell in this `frontend` folder:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Open **http://127.0.0.1:5173**.

To build a production bundle:

```powershell
npm run build
npm run preview
```

The output is written to `dist/`. The Vite proxy is intended for local development. For production hosting, configure equivalent server-side proxy routes or set up the backend CORS policies and API base URLs for the deployed environment.

## 3. Start the backends first

Use your existing startup kit from the project root to start all three services. Confirm these checks work before opening the UI:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8001/health`
- `http://127.0.0.1:8002/health`

The overview page checks health and links to each service's Swagger UI.

## 4. Task 1 API key (only if enabled)

The Task 1 API accepts an optional `X-API-Key` when `KNOWLEDGE_API_KEY` is set on its backend. If the backend requires it, place the same value in `frontend/.env`:

```env
VITE_TASK1_API_KEY=your_local_knowledge_api_key
```

Restart `npm run dev` after changing `.env`. Never commit `.env` or secrets to GitHub. If Task 1 does not have an API key configured, leave this value blank.

## 5. Task 2 route configuration — important

The complete Task 2 application route file was not included in the source bundle available when this frontend was assembled. The available artifacts included Task 2 test/evaluation files and service/database modules, but not the complete running API entry point. Therefore, Task 2 route paths cannot be guaranteed from the available source alone.

The frontend starts with these common REST route defaults:

```env
VITE_TASK2_EMAILS_PATH=/emails
VITE_TASK2_PROCESS_PATH=/emails/process
VITE_TASK2_REVIEW_SUFFIX=/review
VITE_TASK2_FEEDBACK_SUFFIX=/feedback
VITE_TASK2_SEND_SUFFIX=/send
```

Check **http://127.0.0.1:8001/docs** and match these paths and payloads to your actual Task 2 API. If your routes differ, edit `frontend/.env` and restart Vite. The email-list route expects an array or an object containing `items`, `emails`, `results`, or `data`. The email process form sends:

```json
{
  "sender": "customer@example.com",
  "subject": "Question subject",
  "body": "Customer email body",
  "conversation_context": "Optional previous conversation"
}
```

Review/feedback/send paths are configurable as suffixes because the exact Task 2 route contract needs to be confirmed against your local Swagger page. If a call returns `404`, the frontend shows the error and you should correct the route setting rather than change backend behavior blindly.

## 6. API routes used by Task 1 and Task 3

### Task 1 — Knowledge Brain (`8000`)

- `GET /health`
- `POST /query` body: `{ "question": "...", "top_k": 6 }`
- `GET /escalations?status=open&limit=100`
- `POST /escalations/{id}/resolve` body: `{ "answer": "...", "sources": [] }`
- `POST /ingestion/run`
- `GET /ingestion/status`

### Task 3 — Meeting-to-Scope (`8002`)

- `GET /health`
- `POST /projects` body: `{ "client_name": "...", "project_name": "...", "transcript": "...", "meeting_id": "meeting-a" }`
- `GET /projects/{project_id}`
- `POST /projects/{project_id}/approve` body: `{ "version": 1, "reviewer": "...", "notes": "..." }`
- `POST /projects/{project_id}/meetings/follow-up` body: `{ "transcript": "...", "meeting_id": "meeting-c" }`
- `POST /projects/{project_id}/proposal/send` body: `{ "version": 1, "reviewer": "..." }`
- `GET /projects/{project_id}/audit`

## 7. Development structure

```text
frontend/
├── index.html
├── package.json
├── vite.config.js          # local proxy to backend ports 8000/8001/8002
├── .env.example
└── src/
    ├── App.jsx             # app shell, navigation, overview and health checks
    ├── styles.css          # responsive visual design, effects, motion and themes
    ├── components/         # shared buttons, status, notices, JSON viewer
    ├── pages/
    │   ├── KnowledgeChat.jsx
    │   ├── InboxReview.jsx
    │   └── ScopeBuilder.jsx
    └── services/api.js     # fetch wrapper and service paths
```

## 8. Notes

- The UI uses real API calls, not mocked AI results. Sample transcript/email text is only prefilled input that you can edit before submitting.
- Keep human review in the workflow. Do not use this UI to automatically send sensitive or unsupported responses.
- The Task 2 route defaults must be confirmed in your running `/docs` page before calling that integration complete.
- The local Vite proxy only applies while running the Vite development server. Do not deploy it as if it were a production API gateway.
