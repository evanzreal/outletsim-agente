import os
import httpx
from langchain_core.messages import BaseMessage

CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "https://chatwoot.valorgarantido.com")
CHATWOOT_ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID", "3")
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "")
CHATWOOT_INBOX_ID = int(os.getenv("CHATWOOT_INBOX_ID", "8"))

# Sessões em memória: conversation_id → histórico de mensagens LangChain
_sessions: dict[int, list[BaseMessage]] = {}


def get_history(conversation_id: int) -> list[BaseMessage]:
    return list(_sessions.get(conversation_id, []))


def save_history(conversation_id: int, messages: list[BaseMessage]) -> None:
    # Mantém no máximo 40 mensagens por sessão para não estourar contexto
    _sessions[conversation_id] = messages[-40:]


def send_message(conversation_id: int, content: str) -> dict:
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = {"api_access_token": CHATWOOT_API_TOKEN}
    payload = {"content": content, "message_type": "outgoing", "private": False}
    resp = httpx.post(url, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def toggle_conversation_status(conversation_id: int, status: str = "open") -> None:
    """Garante que a conversa está aberta antes de responder."""
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/toggle_status"
    headers = {"api_access_token": CHATWOOT_API_TOKEN}
    httpx.post(url, json={"status": status}, headers=headers, timeout=10)
