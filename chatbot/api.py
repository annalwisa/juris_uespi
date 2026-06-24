"""API REST do chatbot UESPI (FastAPI) para o frontend."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chatbot.chain import get_answer
from chatbot.status import status_message
from chatbot.warmup import start_warmup_background


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_warmup_background()
    yield


app = FastAPI(
    title="Chat UESPI API",
    description="Assistente sobre a Universidade Estadual do Piauí",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[HistoryMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str


class StatusResponse(BaseModel):
    status_markdown: str


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/status", response_model=StatusResponse)
def status():
    return StatusResponse(status_markdown=status_message())


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    text = body.message.strip()
    if not text:
        return ChatResponse(reply="Digite sua pergunta sobre a UESPI.")

    history = [{"role": m.role, "content": m.content} for m in body.history]
    reply = get_answer(text, history)
    return ChatResponse(reply=reply)


def main():
    import os

    import uvicorn

    # Padrão restrito a loopback; defina API_HOST=0.0.0.0 explicitamente
    # ao expor o serviço (ex.: dentro de um container).
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(
        "chatbot.api:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
