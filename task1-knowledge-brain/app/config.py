"""Environment-backed configuration for the Knowledge Brain."""
import os
from dotenv import load_dotenv

# Load .env before creating settings so imports never capture empty values.
load_dotenv()

class Settings:
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_URI = os.getenv("QDRANT_URI")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "ai-tech-consultant")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    KNOWLEDGE_API_KEY = os.getenv("KNOWLEDGE_API_KEY")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4.1")
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "auto")
    ESCALATION_DB_PATH = os.getenv("ESCALATION_DB_PATH", "data/escalations.sqlite3")

settings = Settings()
