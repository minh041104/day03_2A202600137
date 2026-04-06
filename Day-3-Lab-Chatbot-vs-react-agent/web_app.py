import os
import uuid
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.agent.agent import ReActAgent
from src.core.openai_provider import OpenAIProvider
from src.core.gemini_provider import GeminiProvider
from src.core.local_provider import LocalProvider
from src.core.mock_provider import MockProvider


load_dotenv()


def _build_provider():
    provider = (os.getenv("DEFAULT_PROVIDER") or "openai").strip().lower()
    model = (os.getenv("DEFAULT_MODEL") or "gpt-4o").strip()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return MockProvider()
        return OpenAIProvider(model_name=model, api_key=api_key)

    if provider in ("google", "gemini"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return MockProvider()
        return GeminiProvider(model_name=model or "gemini-1.5-flash", api_key=api_key)

    if provider == "local":
        model_path = os.getenv("LOCAL_MODEL_PATH")
        if not model_path:
            return MockProvider()
        return LocalProvider(model_path=model_path)

    return MockProvider()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str


class ResetRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class ResetResponse(BaseModel):
    ok: bool = True


app = FastAPI(title="Restaurant Booking Agent UI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_agents_lock = threading.Lock()
_agents: Dict[str, ReActAgent] = {}


def _get_agent(session_id: str) -> ReActAgent:
    with _agents_lock:
        agent = _agents.get(session_id)
        if agent is None:
            agent = ReActAgent(llm=_build_provider(), max_steps=10)
            _agents[session_id] = agent
        return agent


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "web_static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    agent = _get_agent(session_id)
    reply = agent.run(req.message)
    return ChatResponse(session_id=session_id, reply=reply)


@app.post("/api/reset", response_model=ResetResponse)
def reset(req: ResetRequest):
    with _agents_lock:
        _agents.pop(req.session_id, None)
    return ResetResponse(ok=True)

