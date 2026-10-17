import os

class Settings:
    QDRANT_URI = os.getenv("QDRANT_URI", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "knowledge_brain")
    LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN", "")

settings = Settings()