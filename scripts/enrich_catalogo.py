"""
Enriquece o catálogo buscando specs via Tavily + extração estruturada via LLM.
Gera: especificacoes (texto vendável) + atributos (JSON por categoria).

Uso:
  python scripts/enrich_catalogo.py --limit 5      # testa com 5
  python scripts/enrich_catalogo.py --all           # todos os produtos
  python scripts/enrich_catalogo.py --id 12         # produto específico
  python scripts/enrich_catalogo.py --rerun         # re-processa já enriquecidos
"""
import os, sys, time, argparse, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2, psycopg2.extras, requests
from dotenv import load_dotenv
load_dotenv()

DSN            = os.getenv("DATABASE_URL", "postgresql://postgres:GIUasuiejaj82893_@localhost:5432/outletsim")
TAVILY_KEY     = os.getenv("TAVILY_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# ── Schemas de atributos por categoria ───────────────────────────────────────
#
# Cada entrada define os campos que o LLM deve tentar preencher.
# null = não encontrado. Use tipos nativos JSON.

CATEGORY_SCHEMAS = {
    "Memórias": {
        "_desc": "Módulo de memória RAM para servidores e desktops",
        "tipo": "DDR3 | DDR3L | DDR4 | DDR2",
        "capacidade_gb": 0,
        "frequencia_mhz": 0,
        "formato": "DIMM | RDIMM | LRDIMM | SODIMM | ECC DIMM",
        "ecc": True,
        "registered": False,
        "tensao_v": 1.5,
        "pinos": 240,
        "latencia_cl": None,
        "compatibilidade_servidores": [],
        "obs": None,
    },
    "HD/SSD": {
        "_desc": "Disco rígido ou SSD para servidores",
        "tipo": "HD | SSD",
        "interface": "SAS | SATA | NVMe",
        "capacidade": "600GB",
        "fator_forma": "2.5\" | 3.5\"",
        "rpm": None,
        "velocidade_leitura_mbps": None,
        "velocidade_escrita_mbps": None,
        "cache_mb": None,
        "iops": None,
        "hot_swap": True,
        "compatibilidade_servidores": ["Dell PowerEdge", "HP ProLiant"],
        "obs": None,
    },
    "Firewall": {
        "_desc": "Appliance de segurança de rede",
        "marca": "",
        "linha": "",
        "throughput_firewall_gbps": None,
        "throughput_ngfw_gbps": None,
        "throughput_vpn_gbps": None,
        "portas_ethernet": None,
        "portas_sfp": None,
        "portas_poe": None,
        "vpn_ipsec": True,
        "vpn_ssl": True,
        "utm": True,
        "ids_ips": True,
        "usuarios_recomendados": None,
        "sessoes_simultaneas": None,
        "novas_conexoes_por_seg": None,
        "obs": None,
    },
    "Telefonia": {
        "_desc": "Telefone IP, digital ou analógico",
        "tipo": "IP | Digital | Analógico | PABX | Gateway",
        "protocolo": "SIP | H.323 | Digital | Analógico",
        "contas_sip": None,
        "display": None,
        "display_colorido": False,
        "poe": True,
        "gigabit": False,
        "viva_voz": True,
        "teclas_programaveis": None,
        "teclas_dsss": None,
        "headset_rj9": True,
        "bluetooth": False,
        "usb": False,
        "codecs": [],
        "compatibilidade": [],
        "obs": None,
    },
    "Body Cam": {
        "_desc": "Câmera corporal para agentes de segurança",
        "resolucao_video": "1080p | 720p | 4K",
        "fps": None,
        "armazenamento_gb": None,
        "bateria_horas": None,
        "ip_rating": None,
        "gps": False,
        "wifi": False,
        "bluetooth": False,
        "4g_lte": False,
        "visao_noturna": False,
        "audio_bidirecional": False,
        "transmissao_ao_vivo": False,
        "obs": None,
    },
    "Coletor de Dados": {
        "_desc": "Coletor de dados portátil para operações logísticas",
        "marca": "",
        "os": "",
        "leitor_codigo": "1D | 2D | QR | RFID",
        "display_polegadas": None,
        "display_touch": True,
        "wifi_802_11": "",
        "bluetooth": True,
        "4g_lte": False,
        "nfc": False,
        "ip_rating": None,
        "mil_std": None,
        "bateria_mah": None,
        "bateria_horas": None,
        "camera_mp": None,
        "ram_gb": None,
        "armazenamento_gb": None,
        "obs": None,
    },
    "Conferência": {
        "_desc": "Equipamento de videoconferência ou audioconferência",
        "tipo": "camera | speakerphone | kit_videoconferencia | microfone",
        "resolucao_camera": None,
        "campo_visao_graus": None,
        "zoom_optico": None,
        "zoom_digital": None,
        "microfones_inclusos": None,
        "alcance_microfone_m": None,
        "cancelamento_ruido": True,
        "viva_voz": True,
        "usb": True,
        "bluetooth": False,
        "wifi": False,
        "hdmi": False,
        "teams_certificado": False,
        "zoom_certificado": False,
        "participantes_recomendados": None,
        "obs": None,
    },
    "Segurança e CFTV": {
        "_desc": "DVR, NVR, câmera ou equipamento de segurança",
        "tipo": "DVR | NVR | MDVR | camera_bullet | camera_dome | alarme | outro",
        "canais": None,
        "resolucao_max": None,
        "compressao": None,
        "baias_hd": None,
        "poe_portas": None,
        "acesso_remoto": True,
        "app_mobile": True,
        "hdmi_out": True,
        "ip_rating": None,
        "visao_noturna_m": None,
        "resolucao_mp": None,
        "lente_mm": None,
        "varifocal": False,
        "obs": None,
    },
    "Controle de Acesso": {
        "_desc": "Controlador de acesso, biometria, porteiro ou fechadura",
        "tipo": "controlador | leitor_biometrico | video_porteiro | fechadura | sensor | receptor | alarme",
        "tecnologias": [],
        "capacidade_usuarios": None,
        "portas_gerenciadas": None,
        "protocolos": [],
        "conectividade": [],
        "ip_rating": None,
        "alimentacao_v": None,
        "obs": None,
    },
    "Equipamentos Financeiros": {
        "_desc": "Equipamento para operações financeiras",
        "tipo": "impressora_cheques | validadora_cedulas | outro",
        "velocidade_notas_min": None,
        "capacidade_alimentacao": None,
        "capacidade_empilhamento": None,
        "moedas_suportadas": [],
        "display": None,
        "conectividade": [],
        "dimensoes_mm": None,
        "peso_kg": None,
        "obs": None,
    },
    "Áudio Visual": {
        "_desc": "Projetor, mesa de som ou equipamento audiovisual",
        "tipo": "projetor | mesa_som | outro",
        "tecnologia": None,
        "resolucao": None,
        "luminosidade_lumens": None,
        "contraste": None,
        "canais_som": None,
        "entradas": [],
        "saidas": [],
        "obs": None,
    },
    "Casa, Móveis e Decoração": {
        "_desc": "Móvel, tapete ou item de decoração",
        "tipo": "tapete | cadeira | sofa | mesa | outro",
        "material": None,
        "dimensoes": None,
        "cor": None,
        "estilo": None,
        "obs": None,
    },
}

DEFAULT_SCHEMA = {
    "tipo": None,
    "especificacoes_principais": [],
    "compatibilidade": [],
    "obs": None,
}


def get_schema(categoria):
    for key in CATEGORY_SCHEMAS:
        if key.lower() in categoria.lower() or categoria.lower() in key.lower():
            return CATEGORY_SCHEMAS[key]
    return DEFAULT_SCHEMA


# ── DB ────────────────────────────────────────────────────────────────────────

def _conn():
    return psycopg2.connect(DSN)


def ensure_columns():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE catalogo_produtos ADD COLUMN IF NOT EXISTS especificacoes TEXT")
            cur.execute("ALTER TABLE catalogo_produtos ADD COLUMN IF NOT EXISTS atributos JSONB")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_catalogo_atributos
                ON catalogo_produtos USING GIN(atributos)
            """)


def fetch_products(limit=None, product_id=None, only_missing=True):
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            where = "WHERE ativo = TRUE"
            if only_missing:
                where += " AND atributos IS NULL"
            if product_id:
                where += f" AND id = {int(product_id)}"
            lim = f"LIMIT {int(limit)}" if limit else ""
            cur.execute(f"""
                SELECT id, categoria, titulo, descricao
                FROM catalogo_produtos {where}
                ORDER BY id {lim}
            """)
            return [dict(r) for r in cur.fetchall()]


def save_enrichment(product_id, especificacoes, atributos):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE catalogo_produtos
                   SET especificacoes = %s, atributos = %s
                   WHERE id = %s""",
                (especificacoes, json.dumps(atributos, ensure_ascii=False), product_id)
            )


# ── Tavily ────────────────────────────────────────────────────────────────────

def tavily_search(titulo, categoria):
    query = f"{titulo} especificações técnicas ficha técnica datasheet"
    resp = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": 6,
            "include_answer": True,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    parts = []
    if data.get("answer"):
        parts.append(f"Resumo: {data['answer']}")
    for r in data.get("results", [])[:5]:
        snippet = r.get("content", "").strip()
        if snippet:
            parts.append(f"[{r.get('title', '')}]\n{snippet[:700]}")

    return "\n\n".join(parts)


# ── LLM ───────────────────────────────────────────────────────────────────────

def enrich_with_llm(titulo, categoria, descricao, search_context):
    schema = get_schema(categoria)
    schema_str = json.dumps({k: v for k, v in schema.items() if k != "_desc"},
                            ensure_ascii=False, indent=2)
    cat_desc = schema.get("_desc", categoria)

    prompt = f"""Você é especialista em tecnologia e vai enriquecer dados de um produto para um e-commerce outlet.

Produto: {titulo}
Categoria: {categoria} ({cat_desc})
{f'Descrição atual: {descricao}' if descricao else ''}

Informações encontradas na web:
{search_context[:4000] if search_context else 'Nenhuma informação encontrada.'}

---

Sua tarefa é retornar um JSON com DOIS campos:

1. "especificacoes": texto corrido em português (máximo 130 palavras), focado em vender o produto.
   - Destaque diferenciais, performance e casos de uso
   - Seja específico: números, velocidades, capacidades reais
   - Não invente — omita o que não souber
   - Sem bullet points, sem títulos, sem introdução genérica

2. "atributos": preencha o schema abaixo com os valores reais do produto.
   - Use null para campos desconhecidos (não invente valores)
   - Arrays vazios [] se não souber compatibilidades
   - Booleanos: true/false
   - Números sem unidade (coloque a unidade no nome do campo)

Schema de atributos para esta categoria:
{schema_str}

Retorne APENAS o JSON válido, sem markdown, sem explicações."""

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 600,
            "response_format": {"type": "json_object"},
        },
        timeout=25,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    return json.loads(raw)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",  type=int,  help="Enriquecer N produtos sem atributos")
    parser.add_argument("--all",    action="store_true", help="Todos sem atributos")
    parser.add_argument("--id",     type=int,  help="Produto específico pelo ID")
    parser.add_argument("--rerun",  action="store_true", help="Re-processa já enriquecidos")
    parser.add_argument("--delay",  type=float, default=1.5, help="Segundos entre requisições")
    args = parser.parse_args()

    ensure_columns()

    only_missing = not args.rerun
    if args.id:
        products = fetch_products(product_id=args.id, only_missing=False)
    elif args.all:
        products = fetch_products(only_missing=only_missing)
    elif args.limit:
        products = fetch_products(limit=args.limit, only_missing=only_missing)
    else:
        parser.print_help()
        return

    if not products:
        print("Nenhum produto para enriquecer.")
        return

    print(f"\n🔍 Enriquecendo {len(products)} produto(s)...\n")

    ok = err = 0
    for i, p in enumerate(products, 1):
        print(f"[{i}/{len(products)}] ID {p['id']} | {p['categoria']} — {p['titulo']}")
        try:
            context   = tavily_search(p["titulo"], p["categoria"])
            result    = enrich_with_llm(p["titulo"], p["categoria"], p.get("descricao"), context)

            specs     = result.get("especificacoes", "")
            atributos = result.get("atributos", {})

            # remove campo interno _desc se LLM incluiu
            atributos.pop("_desc", None)

            save_enrichment(p["id"], specs, atributos)

            print(f"  ✓ specs: {specs[:100]}…")
            # mostra atributos não-nulos
            filled = {k: v for k, v in atributos.items() if v not in (None, [], "", False)}
            print(f"  ✓ atributos preenchidos: {list(filled.keys())}")
            ok += 1
        except Exception as e:
            print(f"  ✗ Erro: {e}")
            err += 1

        if i < len(products):
            time.sleep(args.delay)

    print(f"\n✅ {ok} enriquecidos | ❌ {err} erros\n")


if __name__ == "__main__":
    main()
