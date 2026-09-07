"""
Fluxo do Lucas — atendimento WhatsApp ativo da OutletSIM.
Máquina de estados: o agente inicia a conversa (fluxo ativo).
"""
import os
from app import db, whatsapp

_SUPA = "https://lgafeufowivtvhwsozhw.supabase.co/storage/v1/object/public/outletsim"

VIDEO_BOAS_VINDAS = f"{_SUPA}/lucas/video1.mp4"

FOTOS_CAMPANHAS = [
    f"{_SUPA}/lucas/foto1.jpg",
    f"{_SUPA}/lucas/foto2.jpg",
    f"{_SUPA}/lucas/foto3.jpg",
]

LINK_VIP = "https://chat.whatsapp.com/EDIvCbatq2RD4FccvY81Ns"

TEXTO_BOAS_VINDAS = (
    "Olá, bem vindo!\n\n"
    "Prazer, sou o Lucas, representante comercial aqui da OutletSim e vou te auxiliar na sua experiência conosco!\n\n"
    "Antes de começarmos, queria deixar o convite para entrar em nossa nova comunidade cheia de ofertas e promoções!\n\n"
    f"{LINK_VIP}\n\n"
    "Agora sim vou lhe enviar nossas principais promoções do mês!"
)

PERGUNTA_PRODUTO = "Me conta, qual equipamento está buscando?"

# Etapas do fluxo
STEP_WELCOME     = "welcome"     # aguardando primeira resposta após boas-vindas
STEP_CONSULTING  = "consulting"  # modo consultivo com agente LLM


def _get_step(session: list[dict]) -> str:
    for m in reversed(session):
        if m.get("__step"):
            return m["__step"]
    return STEP_CONSULTING


def _set_step(session: list[dict], step: str) -> list[dict]:
    return session + [{"__step": step}]


def handle(phone: str, text: str) -> str | None:
    """
    Processa mensagem recebida no fluxo do Lucas.
    Retorna None se já tratou internamente, "__use_agent__" para delegar ao LLM.
    """
    session = db.get_wa_session(phone)
    step = _get_step(session)

    if step == STEP_WELCOME:
        # qualquer resposta após boas-vindas → modo consultivo
        session = _set_step(session, STEP_CONSULTING)
        db.save_wa_session(phone, session[-40:])
        return "__use_agent__"

    return "__use_agent__"


def is_new_contact(phone: str) -> bool:
    session = db.get_wa_session(phone)
    return not session  # só dispara boas-vindas pra sessão vazia


def send_welcome(phone: str) -> None:
    """Envia o fluxo ativo de boas-vindas: vídeo → texto → fotos → pergunta."""
    whatsapp.send_media(phone, VIDEO_BOAS_VINDAS, "video")
    whatsapp.send_text(phone, TEXTO_BOAS_VINDAS)
    for foto in FOTOS_CAMPANHAS:
        whatsapp.send_media(phone, foto, "image")
    whatsapp.send_text(phone, PERGUNTA_PRODUTO)

    session = [{"__step": STEP_WELCOME}]
    db.save_wa_session(phone, session)
