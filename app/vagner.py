"""
Fluxo do Vagner — atendimento WhatsApp da OutletSIM.
Máquina de estados para novos contatos (sem histórico).
"""
import os
from app import db, whatsapp

_SUPA_PUBLIC = "https://lgafeufowivtvhwsozhw.supabase.co/storage/v1/object/public/outletsim"

CAMPANHAS_PADRAO = [
    f"{_SUPA_PUBLIC}/campanhas/padrao/img1.jpg",
    f"{_SUPA_PUBLIC}/campanhas/padrao/img2.jpg",
    f"{_SUPA_PUBLIC}/campanhas/padrao/img3.jpg",
]

CAMPANHAS_ESPECIAIS = [
    f"{_SUPA_PUBLIC}/campanhas/especiais/img1.jpg",
    f"{_SUPA_PUBLIC}/campanhas/especiais/img2.jpg",
    f"{_SUPA_PUBLIC}/campanhas/especiais/img3.jpg",
    f"{_SUPA_PUBLIC}/campanhas/especiais/img4.jpg",
    (f"{_SUPA_PUBLIC}/campanhas/especiais/vid1.mp4", "video"),
    (f"{_SUPA_PUBLIC}/campanhas/especiais/vid2.mp4", "video"),
]

LINK_VIP = "https://chat.whatsapp.com/EDIvCbatq2RD4FccvY81Ns"

# Etapas do fluxo
STEP_WELCOME       = "welcome"       # aguardando nome
STEP_CAMPAIGNS     = "campaigns"     # nome recebido, enviando campanhas
STEP_ASK_PRODUCT   = "ask_product"   # campanhas enviadas, perguntando produto
STEP_CONSULTING    = "consulting"    # modo livre com catálogo


def _get_step(session: list[dict]) -> str:
    for m in reversed(session):
        if m.get("__step"):
            return m["__step"]
    return STEP_WELCOME if not session else STEP_CONSULTING


def _set_step(session: list[dict], step: str) -> list[dict]:
    return session + [{"__step": step}]


def _get_name(session: list[dict]) -> str:
    for m in session:
        if m.get("__name"):
            return m["__name"]
    return ""


def _send_campaigns(phone: str) -> None:
    for item in CAMPANHAS_PADRAO:
        whatsapp.send_media(phone, item, "image")

    for item in CAMPANHAS_ESPECIAIS:
        if isinstance(item, tuple):
            url, media_type = item
            whatsapp.send_media(phone, url, media_type)
        else:
            whatsapp.send_media(phone, item, "image")


def handle(phone: str, text: str) -> str | None:
    """
    Processa a mensagem dentro do fluxo do Vagner.
    Retorna a resposta de texto (já enviada internamente via whatsapp.send_text),
    ou None se não houver resposta de texto (só mídia).
    """
    session = db.get_wa_session(phone)
    step = _get_step(session)

    if step == STEP_WELCOME:
        # aguardando nome do cliente
        name = text.strip().split()[0].capitalize()
        session = _set_step(session + [{"__name": name}], STEP_CAMPAIGNS)

        reply = (
            f"Prazer, {name}! 😊\n\n"
            f"Antes de tudo, entra no nosso grupo VIP do WhatsApp — "
            f"lá saem as ofertas antes de todo mundo:\n{LINK_VIP}"
        )
        whatsapp.send_text(phone, reply)

        # envia campanhas
        _send_campaigns(phone)

        # avança para próxima etapa
        session = _set_step(session, STEP_ASK_PRODUCT)
        db.save_wa_session(phone, session[-40:])

        ask = "Olha as ofertas de agosto 🔥\n\nE me conta: o que você está procurando hoje? Pode ser o nome do modelo ou pra que você vai usar 🙂"
        whatsapp.send_text(phone, ask)
        return None  # já enviamos tudo diretamente

    elif step == STEP_ASK_PRODUCT or step == STEP_CONSULTING:
        # modo consultivo — passa para o agente LLM com histórico limpo de mensagens
        session = _set_step(session, STEP_CONSULTING)
        db.save_wa_session(phone, session[-40:])
        return "__use_agent__"  # sinaliza para o webhook usar o chat() da Isabela

    else:
        return "__use_agent__"


def is_new_contact(phone: str) -> bool:
    session = db.get_wa_session(phone)
    return not session or _get_step(session) == STEP_WELCOME


def send_welcome(phone: str) -> None:
    """Envia a saudação inicial pedindo o nome."""
    msg = "Olá! Tudo bem? Aqui é o Vagner, da OutletSIM 👋 Antes da gente continuar, qual seu nome?"
    whatsapp.send_text(phone, msg)
    session = [{"__step": STEP_WELCOME}]
    db.save_wa_session(phone, session)
