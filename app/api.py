import os
import secrets
import httpx
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.agent import chat
from app.tray import client as tray_client
from app.admin import meta_agent as admin_agent

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
