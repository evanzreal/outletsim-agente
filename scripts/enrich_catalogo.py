"""
Enriquece o catálogo buscando specs via Tavily + resumo via LLM.
Uso:
  python scripts/enrich_catalogo.py --limit 5      # testa com 5
  python scripts/enrich_catalogo.py --all           # todos os produtos
  python scripts/enrich_catalogo.py --id 12         # produto específico
"""
import os, sys, time, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2, psycopg2.extras, requests
from dotenv import load_dotenv
load_dotenv()

DSN            = os.getenv("DATABASE_URL", "postgresql://postgres:GIUasuiejaj82893_@localhost:5432/outletsim")
TAVILY_KEY     = os.getenv("TAVILY_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# ── helpers ───────────────────────────────────────────────────────────────────

def _conn():
    return psycopg2.connect(DSN)


def ensure_column():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE catalogo_produtos
                ADD COLUMN IF NOT EXISTS especificacoes TEXT
            """)


def fetch_products(limit=None, product_id=None, only_missing=True):
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            where = "WHERE ativo = TRUE"
            if only_missing:
                where += " AND especificacoes IS NULL"
            if product_id:
                where += f" AND id = {int(product_id)}"
            lim = f"LIMIT {int(limit)}" if limit else ""
            cur.execute(f"SELECT id, categoria, titulo, descricao FROM catalogo_produtos {where} ORDER BY id {lim}")
            return [dict(r) for r in cur.fetchall()]


def save_specs(product_id, especificacoes):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE catalogo_produtos SET especificacoes = %s WHERE id = %s",
                (especificacoes, product_id)
            )


# ── Tavily ────────────────────────────────────────────────────────────────────

def tavily_search(titulo, categoria):
    query = f"{titulo} especificações técnicas"
    resp = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": 5,
            "include_answer": True,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    parts = []
    if data.get("answer"):
        parts.append(f"Resumo: {data['answer']}")
    for r in data.get("results", [])[:4]:
        snippet = r.get("content", "").strip()
        if snippet:
            parts.append(f"[{r.get('title', '')}]\n{snippet[:600]}")

    return "\n\n".join(parts)


# ── LLM ───────────────────────────────────────────────────────────────────────

def extract_specs(titulo, categoria, search_context):
    if not search_context.strip():
        return None

    prompt = f"""Produto: {titulo}
Categoria: {categoria}

Informações encontradas na web:
{search_context[:3500]}

---

Com base nas informações acima, escreva as especificações técnicas do produto de forma clara e concisa (máximo 120 palavras).
Inclua somente dados relevantes para um comprador: interface, capacidade, velocidade, conectividade, compatibilidade, fator de forma, e diferenciais.
Se as informações forem insuficientes, escreva apenas o que encontrou — não invente.
Responda em português, sem introdução, sem títulos, sem bullet points."""

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 200,
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",  type=int, help="Enriquecer N produtos (sem especificacoes)")
    parser.add_argument("--all",    action="store_true", help="Enriquecer todos sem especificacoes")
    parser.add_argument("--id",     type=int, help="Enriquecer produto específico pelo ID")
    parser.add_argument("--delay",  type=float, default=1.5, help="Segundos entre requisições (default 1.5)")
    args = parser.parse_args()

    ensure_column()

    if args.id:
        products = fetch_products(product_id=args.id, only_missing=False)
    elif args.all:
        products = fetch_products(only_missing=True)
    elif args.limit:
        products = fetch_products(limit=args.limit, only_missing=True)
    else:
        parser.print_help()
        return

    if not products:
        print("Nenhum produto para enriquecer.")
        return

    print(f"\n🔍 Enriquecendo {len(products)} produto(s)...\n")

    ok = err = 0
    for i, p in enumerate(products, 1):
        print(f"[{i}/{len(products)}] ID {p['id']} — {p['titulo']}")
        try:
            context = tavily_search(p["titulo"], p["categoria"])
            specs   = extract_specs(p["titulo"], p["categoria"], context)

            if specs:
                save_specs(p["id"], specs)
                print(f"  ✓ {specs[:120]}{'…' if len(specs) > 120 else ''}")
                ok += 1
            else:
                print("  ⚠ Nenhuma info encontrada — pulando.")
                err += 1
        except Exception as e:
            print(f"  ✗ Erro: {e}")
            err += 1

        if i < len(products):
            time.sleep(args.delay)

    print(f"\n✅ {ok} enriquecidos | ❌ {err} erros\n")


if __name__ == "__main__":
    main()
