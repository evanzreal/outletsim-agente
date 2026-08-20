"""
Debounce de mensagens WhatsApp por número de telefone.

Cada mensagem nova reseta um timer de 7s. Quando o timer expira,
todas as mensagens acumuladas são concatenadas e processadas juntas.

- Redis: acumula mensagens (compartilhado entre workers)
- asyncio.Task: controla o timer dentro do processo
- Lock Redis: garante que só um worker processa o batch
"""

import asyncio
import os
import redis.asyncio as aioredis

BATCH_DELAY = 7  # segundos após a última mensagem

_redis: aioredis.Redis | None = None
_tasks: dict[str, asyncio.Task] = {}
_processor = None  # callable(phone, text) — injetado em runtime


def init(processor_fn):
    """Deve ser chamado no startup do FastAPI."""
    global _processor
    _processor = processor_fn


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True,
        )
    return _redis


async def receive(phone: str, text: str) -> None:
    """Registra uma mensagem e reseta o timer de debounce."""
    r = _get_redis()
    await r.rpush(f"wa:batch:{phone}", text)

    # cancela timer anterior (debounce)
    if phone in _tasks and not _tasks[phone].done():
        _tasks[phone].cancel()

    _tasks[phone] = asyncio.create_task(_fire(phone))


async def _fire(phone: str) -> None:
    """Aguarda 7s e processa o batch (com lock para evitar duplo processamento)."""
    await asyncio.sleep(BATCH_DELAY)

    r = _get_redis()

    # lock distribuído: só um worker processa
    acquired = await r.set(f"wa:lock:{phone}", "1", nx=True, ex=30)
    if not acquired:
        return

    try:
        messages = await r.lrange(f"wa:batch:{phone}", 0, -1)
        await r.delete(f"wa:batch:{phone}")
    finally:
        await r.delete(f"wa:lock:{phone}")

    if not messages:
        return

    combined = "\n".join(messages)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _processor, phone, combined)
