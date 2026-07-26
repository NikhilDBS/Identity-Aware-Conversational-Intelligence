from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.memory.neo4j_client import get_driver, close_driver
from app.memory.schema import init_schema
from app.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    driver = get_driver()
    init_schema(driver)
    yield
    close_driver()


app = FastAPI(title="IACI", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    driver = get_driver()
    try:
        reply = run_pipeline(driver, req.user_id, req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ChatResponse(reply=reply)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/memory/{user_id}")
def get_memory(user_id: str) -> dict:
    from app.memory.retrieval import retrieve_context
    driver = get_driver()
    return retrieve_context(driver, user_id)
