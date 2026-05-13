import os
import re
import httpx
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_HOST = os.getenv("TRAY_API_HOST", "")
CONSUMER_KEY = os.getenv("TRAY_CONSUMER_KEY", "")
CONSUMER_SECRET = os.getenv("TRAY_CONSUMER_SECRET", "")

_access_token = os.getenv("TRAY_ACCESS_TOKEN", "")
_refresh_token = os.getenv("TRAY_REFRESH_TOKEN", "")
_token_expires_at = datetime.fromisoformat(os.getenv("TRAY_TOKEN_EXPIRES_AT", "2000-01-01T00:00:00"))

_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


def _persist_tokens(access_token: str, refresh_token: str, expires_at: datetime, refresh_expires_at: datetime, api_host: str, store_id: str) -> None:
    """Salva os tokens novos no .env em disco para sobreviver a restarts."""
    global API_HOST
    if not _ENV_FILE.exists():
        return
    content = _ENV_FILE.read_text()

    def replace_or_append(text: str, key: str, value: str) -> str:
        pattern = rf"^{key}=.*$"
        replacement = f"{key}={value}"
        if re.search(pattern, text, re.MULTILINE):
            return re.sub(pattern, replacement, text, flags=re.MULTILINE)
        return text + f"\n{replacement}"

    content = replace_or_append(content, "TRAY_ACCESS_TOKEN", access_token)
    content = replace_or_append(content, "TRAY_REFRESH_TOKEN", refresh_token)
    content = replace_or_append(content, "TRAY_TOKEN_EXPIRES_AT", expires_at.isoformat())
    content = replace_or_append(content, "TRAY_REFRESH_EXPIRES_AT", refresh_expires_at.isoformat())
    content = replace_or_append(content, "TRAY_API_HOST", api_host)
    content = replace_or_append(content, "TRAY_STORE_ID", store_id)
    _ENV_FILE.write_text(content)
    API_HOST = api_host


def activate_from_code(code: str, store_api_host: str) -> dict:
    """Troca um authorization code por access_token + refresh_token. Persiste automaticamente."""
    global _access_token, _refresh_token, _token_expires_at, API_HOST
    resp = httpx.post(f"{store_api_host}/auth", json={
        "consumer_key": CONSUMER_KEY,
        "consumer_secret": CONSUMER_SECRET,
        "code": code,
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    _access_token = data["access_token"]
    _refresh_token = data["refresh_token"]
    _token_expires_at = datetime.fromisoformat(data["date_expiration_access_token"])
    refresh_expires_at = datetime.fromisoformat(data["date_expiration_refresh_token"])
    api_host = data.get("api_host", store_api_host)
    store_id = data.get("store_id", "")
    _persist_tokens(_access_token, _refresh_token, _token_expires_at, refresh_expires_at, api_host, store_id)
    return data


def _refresh_access_token() -> str:
    global _access_token, _refresh_token, _token_expires_at
    resp = httpx.post(f"{API_HOST}/auth", json={
        "consumer_key": CONSUMER_KEY,
        "consumer_secret": CONSUMER_SECRET,
        "refresh_token": _refresh_token,
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    _access_token = data["access_token"]
    _refresh_token = data["refresh_token"]
    _token_expires_at = datetime.fromisoformat(data["date_expiration_access_token"])
    refresh_expires_at = datetime.fromisoformat(data["date_expiration_refresh_token"])
    _persist_tokens(_access_token, _refresh_token, _token_expires_at, refresh_expires_at, API_HOST, os.getenv("TRAY_STORE_ID", ""))
    return _access_token


def _get_token() -> str:
    if datetime.now() >= _token_expires_at:
        return _refresh_access_token()
    return _access_token


def get(path: str, params: dict | None = None) -> dict:
    token = _get_token()
    url = f"{API_HOST}{path}"
    p = {"access_token": token, **(params or {})}
    resp = httpx.get(url, params=p, timeout=15)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.json()
