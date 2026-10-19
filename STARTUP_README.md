# AI Tech Consultant — one-command startup kit

This kit launches the three local services together, using the ports you confirmed are working:

| Task | Health | Swagger |
|---|---|---|
| Task 1 — Knowledge Brain | http://127.0.0.1:8000/health | http://127.0.0.1:8000/docs |
| Task 2 — Inbox Agent | http://127.0.0.1:8001/health | http://127.0.0.1:8001/docs |
| Task 3 — Meeting-to-Scope | http://127.0.0.1:8002/health | http://127.0.0.1:8002/docs |

## Setup

1. Extract this ZIP.
2. Copy `start_all.bat` and `start_all.ps1` into the root folder that contains all three task folders.
3. Ensure the task folders are named `task1-knowledge-brain`, `task2-inbox-agent`, and `task3-meeting-to-scope`, or edit the folder candidates in `start_all.ps1`.
4. Install each task's dependencies in its own environment and configure its `.env` file. Never commit secrets.
5. For Task 1 and Task 3, the script uses each task's `.venv\Scripts\python.exe` if present, otherwise system Python. Task 2 startup is detected from common Node/Python entry points.

## Run all tasks

Double-click `start_all.bat`, or open PowerShell in the project root and run:

```powershell
.\start_all.ps1
```

To avoid opening Swagger automatically:

```powershell
.\start_all.ps1 -NoBrowser
```

The script starts each service as a separate background process, writes stdout/stderr to the `logs/` folder, and checks all three `/health` endpoints for up to 60 seconds.

## Task 2 note

The launcher supports common Task 2 entry points: root `package.json` (`npm run dev` with port argument), `backend/package.json`, `app/main.py`, `main.py`, or `server.js`. The exact Task 2 command can vary by repository. If your working Task 2 command differs, edit that block in `start_all.ps1` to match it. A frontend-only `npm run dev` may not start the API backend; launch both processes if your project separates them.

## Troubleshooting

- **Port already in use:** stop the existing instance before running the launcher again.
- **Health check fails:** inspect the matching `logs/task-*.err.log` and `.out.log` files.
- **Python module missing:** install the task's `requirements.txt` into its `.venv`.
- **Task 1 API calls fail from Task 2/3:** make sure their `TASK1_API_BASE_URL` points to `http://127.0.0.1:8000`.

This is a local development launcher, not a production deployment or process supervisor. The kit has not been executed on your Windows machine; verify the logs and health endpoints after the first run.


### Fix included in this version

The PowerShell launcher now uses `AppArgs` rather than `Args` for the process argument parameter. `Args` conflicts with PowerShell automatic-variable behavior and could cause `Start-Process -ArgumentList` to receive an empty value. The launcher also validates the executable and arguments before starting a service.
