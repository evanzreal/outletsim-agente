import os
import secrets
import httpx
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.agent import chat
from app.tray import client as tray_client
from app.admin import meta_agent as admin_agent
from app import rdstation, whatsapp, db, vagner
from langchain_core.messages import HumanMessage, AIMessage

_RDS_CLIENT_ID     = os.getenv("RDSTATION_CLIENT_ID", "")
_RDS_CLIENT_SECRET = os.getenv("RDSTATION_CLIENT_SECRET", "")
_RDS_REDIRECT_URI  = "https://outletsim.valorgarantido.com/auth/rdstation/callback"
_RDS_TOKEN_FILE    = Path("/opt/outletsim-agente/.rdstation_tokens.json")

STATIC_DIR = Path(__file__).parent / "static"

_security = HTTPBasic()
_ADMIN_USER = os.getenv("ADMIN_USER", "admin")
_ADMIN_PASS = os.getenv("ADMIN_PASS", "Outlet@2026")


def _require_admin(credentials: HTTPBasicCredentials = Depends(_security)):
    ok = (
        secrets.compare_digest(credentials.username.encode(), _ADMIN_USER.encode()) and
        secrets.compare_digest(credentials.password.encode(), _ADMIN_PASS.encode())
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )


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


_HUMAN_TAKEOVER_MSG = (
    "Olá! Seu atendimento foi assumido por um de nossos especialistas. "
    "Em breve alguém da equipe da OutletSIM vai continuar a conversa com você. 😊"
)


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []
    contact_identifier: str | None = None  # e-mail ou telefone do contato na RD Station


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
        # gate: verifica atendimento humano antes de acionar o agente
        if req.contact_identifier and rdstation.is_human_takeover(req.contact_identifier):
            return ChatResponse(response=_HUMAN_TAKEOVER_MSG)

        history = _to_lc_messages(req.history)
        response = chat(req.message, history)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


class AdminChatRequest(BaseModel):
    message: str
    history: list[Message] = []


@app.get("/admin/ofertas")
async def admin_list_offers(_: None = Depends(_require_admin)):
    try:
        from app import db
        return {"ofertas": db.get_active_offers()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/chat", response_model=ChatResponse)
async def admin_chat_endpoint(req: AdminChatRequest, _: None = Depends(_require_admin)):
    try:
        history = [{"role": m.role, "content": m.content} for m in req.history]
        response = admin_agent.chat(req.message, history)
        return ChatResponse(response=response)
    except Exception as e:
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


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Recebe mensagens do WhatsApp via UazAPI e responde com a Isabela."""
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored"}

    msg = payload.get("message", {})

    # ignora mensagens enviadas pela própria instância
    if msg.get("fromMe", True):
        return {"status": "ignored"}

    # aceita apenas mensagens de texto
    msg_type = msg.get("messageType", msg.get("type", ""))
    if msg_type.lower() not in ("conversation", "extendedtextmessage", "text"):
        return {"status": "ignored"}

    text = (msg.get("text") or msg.get("content") or "").strip()
    if not text:
        return {"status": "ignored"}

    # extrai número limpo do sender_pn (ex: "554898672729@s.whatsapp.net" → "554898672729")
    sender_pn = msg.get("sender_pn", "")
    phone = sender_pn.replace("@s.whatsapp.net", "").replace("@c.us", "")
    if not phone:
        phone = "".join(c for c in payload.get("chat", {}).get("phone", "") if c.isdigit())
    if not phone:
        return {"status": "ignored"}

    # gate: verifica atendimento humano na RD Station
    if rdstation.is_human_takeover(phone):
        return {"status": "human_takeover"}

    # fluxo do Vagner (novo contato → sequência de boas-vindas + campanhas)
    if vagner.is_new_contact(phone):
        vagner.send_welcome(phone)
        return {"status": "ok"}

    result = vagner.handle(phone, text)
    if result is None:
        return {"status": "ok"}  # vagner já enviou tudo

    # modo consultivo — usa o agente LLM
    raw_history = db.get_wa_session(phone)
    lc_history = []
    for m in raw_history:
        if m.get("role") == "user":
            lc_history.append(HumanMessage(content=m["content"]))
        elif m.get("role") == "assistant":
            lc_history.append(AIMessage(content=m["content"]))

    response = chat(text, lc_history)

    updated = [m for m in raw_history if not m.get("__step") and not m.get("__name")] + [
        {"role": "user",      "content": text},
        {"role": "assistant", "content": response},
    ]
    db.save_wa_session(phone, updated[-40:])

    whatsapp.send_text(phone, response)
    return {"status": "ok"}


@app.get("/auth/rdstation/authorize")
async def rdstation_authorize():
    """Inicia o fluxo OAuth da RD Station — redireciona para a página de autorização."""
    from urllib.parse import urlencode
    params = urlencode({
        "client_id":    _RDS_CLIENT_ID,
        "redirect_uri": _RDS_REDIRECT_URI,
    })
    return RedirectResponse(f"https://api.rd.services/auth/dialog?{params}")


@app.get("/auth/rdstation/callback")
async def rdstation_callback(request: Request):
    """Callback OAuth da RD Station — troca o code por access_token e salva."""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Parâmetro 'code' ausente.")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.rd.services/auth/token",
            json={
                "client_id":     _RDS_CLIENT_ID,
                "client_secret": _RDS_CLIENT_SECRET,
                "code":          code,
                "redirect_uri":  _RDS_REDIRECT_URI,
            },
            headers={"Content-Type": "application/json"},
            timeout=15,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"RD Station error: {resp.text}")

    tokens = resp.json()
    import json
    _RDS_TOKEN_FILE.write_text(json.dumps(tokens, indent=2))

    return {
        "status": "ok",
        "message": "Autenticação com RD Station concluída.",
        "expires_in": tokens.get("expires_in"),
    }


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin")
async def admin_panel(_: None = Depends(_require_admin)):
    return FileResponse(STATIC_DIR / "admin.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
