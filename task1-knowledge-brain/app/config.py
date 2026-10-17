import os

class Settings:
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
    QDRANT_URI = os.getenv('QDRANT_URI')
    QDRANT_COLLECTION = "ai-tech-consultant"
    
    LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN", "")
    HF_TOKEN = os.getenv("HF_TOKEN")

settings = Settings()