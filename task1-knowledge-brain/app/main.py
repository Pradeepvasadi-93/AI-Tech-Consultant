import os 
import uvicorn
import logfire
from fastapi import FastAPI
from dotenv import load_dotenv
from .config import settings

load_dotenv()

app = FastAPI()

logfire.configure(token=settings.LOGFIRE_TOKEN, service_name="ai-tech-consultant")
logfire.instrument_system_metrics()
logfire.instrument_fastapi(app)

@app.get("/")
def home():
    logfire.info(f"Project Initiated")
    return {"message" : "Enterprise LangGraph RAG API is Live."}

if __name__=="__main__":
    uvicorn.run(app)
