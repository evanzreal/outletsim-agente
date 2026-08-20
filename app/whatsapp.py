import os
import httpx

_SERVER  = os.getenv("UAZAPI_SERVER_URL", "https://biosgroup.uazapi.com")
_TOKEN   = os.getenv("UAZAPI_TOKEN", "")
_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def _h() -> dict:
    return {**_HEADERS, "token": _TOKEN}


def send_text(number: str, text: str) -> dict:
    resp = httpx.post(
        f"{_SERVER}/send/text",
        headers=_h(),
        json={"number": number, "text": text},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def send_media(number: str, url: str, media_type: str = "image", caption: str = "") -> dict:
    resp = httpx.post(
        f"{_SERVER}/send/media",
        headers=_h(),
        json={"number": number, "type": media_type, "file": url, "caption": caption},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
