import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.agent import chat
from app.tray import client as tray_client
from app.integrations import chatwoot

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="OutletSIM Agente de IA", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []


class ChatResponse(BaseModel):
    response: str


def _to_lc_messages(history: list[Message]) -> list[BaseMessage]:
    result = []
    for m in history:
        if m.role == "user":
            result.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            result.append(AIMessage(content=m.content))
    return result


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        history = _to_lc_messages(req.history)
        response = chat(req.message, history)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/chatwoot")
async def chatwoot_webhook(request: Request):
    """
    Recebe eventos do Chatwoot (configurar em Settings → Integrations → Webhooks).
    Processa apenas mensagens recebidas (message_type=0) do inbox configurado.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "invalid_payload"}

    event = payload.get("event")
    if event != "message_created":
        return {"status": "ignored", "event": event}

    # Ignora mensagens enviadas pelo agente (outgoing = 1) ou atividades (2)
    message_type = payload.get("message_type")
    if message_type != 0:
        return {"status": "ignored", "reason": "not_incoming"}

    # Ignora mensagens privadas (notas internas do Chatwoot)
    if payload.get("private"):
        return {"status": "ignored", "reason": "private"}

    conv = payload.get("conversation", {})
    inbox_id = conv.get("inbox_id")
    if inbox_id != chatwoot.CHATWOOT_INBOX_ID:
        return {"status": "ignored", "reason": f"inbox_mismatch (got {inbox_id})"}

    content = (payload.get("content") or "").strip()
    conversation_id = conv.get("id")

    if not content or not conversation_id:
        return {"status": "ignored", "reason": "empty_content"}

    try:
        history = chatwoot.get_history(conversation_id)
        response = chat(content, history)

        new_history = history + [
            HumanMessage(content=content),
            AIMessage(content=response),
        ]
        chatwoot.save_history(conversation_id, new_history)
        chatwoot.send_message(conversation_id, response)

        return {"status": "ok", "conversation_id": conversation_id}
    except Exception as e:
        logger.exception("Erro ao processar webhook Chatwoot conv=%s", conversation_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """
    Endpoint chamado pela Tray após instalação do app.
    A Tray envia: ?code=XXX&api_address=https://loja.commercesuite.com.br
    """
    params = dict(request.query_params)
    code = params.get("code")
    api_address = params.get("api_address", "")

    if not code:
        raise HTTPException(status_code=400, detail="Parâmetro 'code' ausente.")

    api_host = f"{api_address.rstrip('/')}/web_api" if api_address else tray_client.API_HOST

    try:
        data = tray_client.activate_from_code(code, api_host)
        return {
            "status": "ok",
            "message": "Token gerado e salvo com sucesso.",
            "store_id": data.get("store_id"),
            "expires_at": data.get("date_expiration_access_token"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar token: {e}")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
