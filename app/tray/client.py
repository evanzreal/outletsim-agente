import os
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_HOST = os.getenv("TRAY_API_HOST", "")
CONSUMER_KEY = os.getenv("TRAY_CONSUMER_KEY", "")
CONSUMER_SECRET = os.getenv("TRAY_CONSUMER_SECRET", "")

_access_token = os.getenv("TRAY_ACCESS_TOKEN", "")
_refresh_token = os.getenv("TRAY_REFRESH_TOKEN", "")
_token_expires_at = datetime.fromisoformat(os.getenv("TRAY_TOKEN_EXPIRES_AT", "2000-01-01T00:00:00"))


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
