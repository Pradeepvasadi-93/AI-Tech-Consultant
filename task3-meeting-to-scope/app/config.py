import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
TASK1_API_BASE_URL = os.getenv("TASK1_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TASK1_API_KEY = os.getenv("TASK1_API_KEY", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(ROOT / "data" / "meeting_to_scope.db"))
HOURLY_RATE = float(os.getenv("HOURLY_RATE", "0") or 0)
CURRENCY = os.getenv("CURRENCY", "USD")
