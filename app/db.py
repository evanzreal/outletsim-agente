import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

_DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:GIUasuiejaj82893_@localhost:5432/outletsim"
)


def _conn():
    return psycopg2.connect(_DSN)


def get_active_offers() -> list[dict]:
    """Retorna ofertas ativas, ignorando expiradas."""
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, titulo, descricao, preco, link_video, link_produto
                FROM ofertas_ativas
                WHERE ativa = TRUE
                  AND (expira_em IS NULL OR expira_em > NOW())
                ORDER BY criada_em DESC
            """)
            return [dict(r) for r in cur.fetchall()]


def add_offer(titulo: str, descricao: str = None, preco: str = None,
              link_video: str = None, link_produto: str = None,
              expira_em: str = None) -> int:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ofertas_ativas (titulo, descricao, preco, link_video, link_produto, expira_em)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (titulo, descricao, preco, link_video, link_produto, expira_em))
            return cur.fetchone()[0]


def deactivate_offer(offer_id: int) -> bool:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE ofertas_ativas SET ativa = FALSE WHERE id = %s", (offer_id,))
            return cur.rowcount > 0


def update_offer(offer_id: int, **kwargs) -> bool:
    allowed = {"titulo", "descricao", "preco", "link_video", "link_produto", "expira_em"}
    fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE ofertas_ativas SET {set_clause} WHERE id = %s",
                (*fields.values(), offer_id)
            )
            return cur.rowcount > 0
