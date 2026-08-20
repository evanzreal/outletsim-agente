import os
import json
import time
import httpx
from pathlib import Path

_TOKEN_FILE = Path("/opt/outletsim-agente/.rdstation_tokens.json")
_TOKEN_FILE_LOCAL = Path(__file__).parent.parent / ".rdstation_tokens.json"

_CLIENT_ID     = os.getenv("RDSTATION_CLIENT_ID", "")
_CLIENT_SECRET = os.getenv("RDSTATION_CLIENT_SECRET", "")
_BASE_URL      = "https://api.rd.services"


def _token_path() -> Path:
    return _TOKEN_FILE if _TOKEN_FILE.parent.exists() else _TOKEN_FILE_LOCAL


def _load_tokens() -> dict:
    p = _token_path()
    if p.exists():
        return json.loads(p.read_text())
    # fallback: ler das env vars
    return {
        "access_token":  os.getenv("RDSTATION_ACCESS_TOKEN", ""),
        "refresh_token": os.getenv("RDSTATION_REFRESH_TOKEN", ""),
        "expires_at":    0,
    }


def _save_tokens(tokens: dict) -> None:
    _token_path().write_text(json.dumps(tokens, indent=2))
    # sincroniza as env vars em memória para o processo atual
    os.environ["RDSTATION_ACCESS_TOKEN"]  = tokens.get("access_token", "")
    os.environ["RDSTATION_REFRESH_TOKEN"] = tokens.get("refresh_token", "")


def _refresh(refresh_token: str) -> dict:
    resp = httpx.post(
        f"{_BASE_URL}/auth/token",
        json={
            "client_id":     _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
            "refresh_token": refresh_token,
        },
        timeout=15,
    )
    resp.raise_for_status()
    tokens = resp.json()
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 86400) - 300  # 5 min de margem
    return tokens


def get_access_token() -> str:
    """Retorna um access_token válido, fazendo refresh automático se necessário."""
    tokens = _load_tokens()
    expires_at = tokens.get("expires_at", 0)

    if time.time() >= expires_at:
        tokens = _refresh(tokens["refresh_token"])
        _save_tokens(tokens)

    return tokens["access_token"]


def get(path: str, params: dict | None = None) -> dict:
    token = get_access_token()
    resp = httpx.get(
        f"{_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def post(path: str, body: dict) -> dict:
    token = get_access_token()
    resp = httpx.post(
        f"{_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def patch(path: str, body: dict) -> dict:
    token = get_access_token()
    resp = httpx.patch(
        f"{_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
