"""
Enriquece o catálogo buscando specs via Tavily (advanced) + extração estruturada via LLM.
Meta: >= 10 atributos preenchidos por produto.

Uso:
  python scripts/enrich_catalogo.py --limit 5
  python scripts/enrich_catalogo.py --all
  python scripts/enrich_catalogo.py --id 12
  python scripts/enrich_catalogo.py --rerun        # re-processa já enriquecidos
"""
import os, sys, time, argparse, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2, psycopg2.extras, requests
from dotenv import load_dotenv
load_dotenv()

DSN            = os.getenv("DATABASE_URL", "postgresql://postgres:GIUasuiejaj82893_@localhost:5432/outletsim")
TAVILY_KEY     = os.getenv("TAVILY_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# ── Schemas por categoria ─────────────────────────────────────────────────────

CATEGORY_SCHEMAS = {
    "Memórias": """{
  "fabricante": null,
  "tipo": null,
  "capacidade_gb": null,
  "frequencia_mhz": null,
  "velocidade_pc": null,
  "formato": null,
  "pinos": null,
  "tensao_v": null,
  "latencia_cl": null,
  "ecc": null,
  "registered": null,
  "unbuffered": null,
  "ranques": null,
  "largura_banda_gbs": null,
  "compatibilidade_servidores": [],
  "numero_part": null,
  "peso_g": null,
  "obs": null
}""",

    "HD/SSD": """{
  "fabricante": null,
  "tipo": null,
  "interface": null,
  "velocidade_interface": null,
  "capacidade": null,
  "capacidade_bytes": null,
  "fator_forma": null,
  "rpm": null,
  "velocidade_leitura_mbps": null,
  "velocidade_escrita_mbps": null,
  "iops_leitura": null,
  "iops_escrita": null,
  "cache_mb": null,
  "latencia_ms": null,
  "tbw": null,
  "hot_swap": null,
  "altura_mm": null,
  "peso_g": null,
  "compatibilidade_servidores": [],
  "certificacoes": [],
  "numero_part": null,
  "obs": null
}""",

    "Firewall": """{
  "fabricante": null,
  "modelo": null,
  "linha": null,
  "throughput_firewall_gbps": null,
  "throughput_ngfw_gbps": null,
  "throughput_ips_gbps": null,
  "throughput_tls_gbps": null,
  "throughput_vpn_ipsec_gbps": null,
  "throughput_vpn_ssl_gbps": null,
  "portas_ethernet": null,
  "portas_sfp": null,
  "portas_poe": null,
  "vpn_ipsec": null,
  "vpn_ssl": null,
  "utm": null,
  "ids_ips": null,
  "antivirus": null,
  "filtro_web": null,
  "sd_wan": null,
  "usuarios_recomendados": null,
  "sessoes_simultaneas": null,
  "novas_conexoes_por_seg": null,
  "latencia_us": null,
  "rack_1u": null,
  "consumo_watts": null,
  "obs": null
}""",

    "Telefonia": """{
  "fabricante": null,
  "modelo": null,
  "tipo": null,
  "protocolo": null,
  "contas_sip": null,
  "linhas": null,
  "display_polegadas": null,
  "display_resolucao": null,
  "display_colorido": null,
  "poe": null,
  "gigabit": null,
  "portas_ethernet": null,
  "viva_voz": null,
  "teclas_programaveis": null,
  "teclas_linha": null,
  "headset_rj9": null,
  "bluetooth": null,
  "usb": null,
  "wifi": null,
  "codecs": [],
  "peso_g": null,
  "dimensoes_mm": null,
  "alimentacao_v": null,
  "compatibilidade": [],
  "obs": null
}""",

    "Body Cam": """{
  "fabricante": null,
  "modelo": null,
  "resolucao_video": null,
  "fps": null,
  "resolucao_foto_mp": null,
  "armazenamento_interno_gb": null,
  "suporte_sd": null,
  "bateria_mah": null,
  "bateria_horas": null,
  "ip_rating": null,
  "temperatura_operacao": null,
  "gps": null,
  "wifi": null,
  "bluetooth": null,
  "4g_lte": null,
  "visao_noturna": null,
  "visao_noturna_m": null,
  "audio_bidirecional": null,
  "transmissao_ao_vivo": null,
  "campo_visao_graus": null,
  "peso_g": null,
  "dimensoes_mm": null,
  "obs": null
}""",

    "Coletor de Dados": """{
  "fabricante": null,
  "modelo": null,
  "os": null,
  "processador": null,
  "ram_gb": null,
  "armazenamento_gb": null,
  "display_polegadas": null,
  "display_touch": null,
  "display_resolucao": null,
  "leitor_codigo": null,
  "distancia_leitura_cm": null,
  "wifi": null,
  "bluetooth": null,
  "4g_lte": null,
  "nfc": null,
  "rfid": null,
  "ip_rating": null,
  "mil_std": null,
  "queda_m": null,
  "bateria_mah": null,
  "bateria_horas": null,
  "camera_mp": null,
  "gps": null,
  "peso_g": null,
  "dimensoes_mm": null,
  "obs": null
}""",

    "Conferência": """{
  "fabricante": null,
  "modelo": null,
  "tipo": null,
  "resolucao_camera": null,
  "fps": null,
  "campo_visao_graus": null,
  "zoom_optico": null,
  "zoom_digital": null,
  "microfones_inclusos": null,
  "alcance_microfone_m": null,
  "cancelamento_ruido": null,
  "alto_falante": null,
  "usb": null,
  "bluetooth": null,
  "wifi": null,
  "hdmi": null,
  "ethernet": null,
  "teams_certificado": null,
  "zoom_certificado": null,
  "resolucao_maxima_suportada": null,
  "participantes_recomendados": null,
  "peso_g": null,
  "obs": null
}""",

    "Segurança e CFTV": """{
  "fabricante": null,
  "modelo": null,
  "tipo": null,
  "canais": null,
  "resolucao_max": null,
  "compressao": [],
  "baias_hd": null,
  "capacidade_hd_max_tb": null,
  "poe_portas": null,
  "poe_watts_total": null,
  "saida_hdmi": null,
  "saida_vga": null,
  "acesso_remoto": null,
  "app_mobile": null,
  "analise_inteligente": null,
  "ip_rating": null,
  "resolucao_mp": null,
  "lente_mm": null,
  "varifocal": null,
  "visao_noturna_m": null,
  "infravermelho": null,
  "poe_camera": null,
  "audio": null,
  "consumo_watts": null,
  "alimentacao_v": null,
  "dimensoes_mm": null,
  "peso_g": null,
  "obs": null
}""",

    "Controle de Acesso": """{
  "fabricante": null,
  "modelo": null,
  "tipo": null,
  "tecnologias": [],
  "capacidade_usuarios": null,
  "capacidade_cartoes": null,
  "capacidade_eventos": null,
  "portas_gerenciadas": null,
  "leitoras_suportadas": null,
  "protocolos": [],
  "wiegand": null,
  "rs485": null,
  "tcp_ip": null,
  "wifi": null,
  "bluetooth": null,
  "4g": null,
  "display": null,
  "ip_rating": null,
  "alimentacao_v": null,
  "corrente_ma": null,
  "dimensoes_mm": null,
  "peso_g": null,
  "obs": null
}""",

    "Equipamentos Financeiros": """{
  "fabricante": null,
  "modelo": null,
  "tipo": null,
  "velocidade_notas_min": null,
  "capacidade_alimentacao": null,
  "capacidade_empilhamento": null,
  "capacidade_rejeicao": null,
  "moedas_suportadas": [],
  "deteccao_falsificacao": [],
  "display": null,
  "display_polegadas": null,
  "conectividade": [],
  "alimentacao_v": null,
  "consumo_watts": null,
  "dimensoes_mm": null,
  "peso_kg": null,
  "velocidade_impressao_seg": null,
  "obs": null
}""",

    "Áudio Visual": """{
  "fabricante": null,
  "modelo": null,
  "tipo": null,
  "tecnologia": null,
  "resolucao_nativa": null,
  "resolucao_maxima": null,
  "luminosidade_lumens": null,
  "contraste": null,
  "vida_lampada_horas": null,
  "canais_som": null,
  "potencia_watts": null,
  "entradas": [],
  "saidas": [],
  "conectividade": [],
  "dimensoes_mm": null,
  "peso_kg": null,
  "obs": null
}""",

    "Casa, Móveis e Decoração": """{
  "tipo": null,
  "material": null,
  "dimensoes": null,
  "area_m2": null,
  "cor": null,
  "estilo": null,
  "pais_origem": null,
  "marca": null,
  "composicao": null,
  "capacidade_pessoas": null,
  "peso_kg": null,
  "obs": null
}""",
}

DEFAULT_SCHEMA = """{
  "fabricante": null,
  "modelo": null,
  "tipo": null,
  "conectividade": [],
  "alimentacao_v": null,
  "dimensoes_mm": null,
  "peso_g": null,
  "compatibilidade": [],
  "certificacoes": [],
  "obs": null
}"""


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
            cur.execute("CREATE INDEX IF NOT EXISTS idx_catalogo_atributos ON catalogo_produtos USING GIN(atributos)")


def fetch_products(limit=None, product_id=None, only_missing=True):
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            where = "WHERE ativo = TRUE"
            if only_missing:
                where += " AND atributos IS NULL"
            if product_id:
                where += f" AND id = {int(product_id)}"
            lim = f"LIMIT {int(limit)}" if limit else ""
            cur.execute(f"SELECT id, categoria, titulo, descricao FROM catalogo_produtos {where} ORDER BY id {lim}")
            return [dict(r) for r in cur.fetchall()]


def save_enrichment(product_id, especificacoes, atributos):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE catalogo_produtos SET especificacoes=%s, atributos=%s WHERE id=%s",
                (especificacoes, json.dumps(atributos, ensure_ascii=False), product_id)
            )


# ── Tavily ────────────────────────────────────────────────────────────────────

def tavily_search(titulo, categoria):
    # Busca 1: ficha técnica / datasheet (advanced — conteúdo completo)
    r1 = requests.post("https://api.tavily.com/search", json={
        "api_key": TAVILY_KEY,
        "query": f"{titulo} ficha técnica especificações datasheet",
        "search_depth": "advanced",
        "max_results": 4,
        "include_answer": True,
    }, timeout=20)
    r1.raise_for_status()
    d1 = r1.json()

    # Busca 2: manual / características do produto (basic)
    r2 = requests.post("https://api.tavily.com/search", json={
        "api_key": TAVILY_KEY,
        "query": f"{titulo} características técnicas manual",
        "search_depth": "basic",
        "max_results": 3,
        "include_answer": False,
    }, timeout=15)
    r2.raise_for_status()
    d2 = r2.json()

    parts = []
    if d1.get("answer"):
        parts.append(f"[Resumo automático]\n{d1['answer']}")
    for r in d1.get("results", [])[:4]:
        content = r.get("content", "").strip()
        if content:
            parts.append(f"[{r.get('title','')}]\n{content[:800]}")
    for r in d2.get("results", [])[:3]:
        content = r.get("content", "").strip()
        if content:
            parts.append(f"[{r.get('title','')}]\n{content[:500]}")

    return "\n\n".join(parts)


# ── LLM ───────────────────────────────────────────────────────────────────────

def enrich_with_llm(titulo, categoria, descricao, search_context):
    schema = get_schema(categoria)

    prompt = f"""Você é especialista em tecnologia e vai extrair dados de um produto para um e-commerce outlet B2B.

Produto: {titulo}
Categoria: {categoria}
{f'Info adicional: {descricao}' if descricao else ''}

=== CONTEÚDO ENCONTRADO NA WEB ===
{search_context[:5000] if search_context else 'Sem resultados de busca.'}
=== FIM DO CONTEÚDO ===

Retorne um JSON com EXATAMENTE dois campos:

"especificacoes": texto corrido em português (100-150 palavras), focado em vender o produto para empresas.
  - Tom consultivo e técnico — esse texto vai ser lido pela IA de vendas
  - Mencione performance, casos de uso, compatibilidade e diferenciais reais
  - Não repita o nome do produto na primeira palavra
  - Sem bullet points, sem títulos

"atributos": preencha o schema abaixo com os valores reais.
  REGRAS IMPORTANTES:
  - Preencha TODOS os campos que conseguir — o objetivo é ter o máximo de atributos preenchidos
  - Infira a partir do contexto quando razoável (ex: se o título diz "POE", poe=true; se diz "Tipo 2,5", fator_forma="2.5\"")
  - Use null apenas quando realmente não há como saber
  - Números: sem unidade (a unidade está no nome do campo)
  - Arrays: sempre preencha com o que encontrou, mesmo que seja só 1 item
  - Booleanos: true/false (não null) quando dá pra inferir do contexto

Schema:
{schema}

Retorne SOMENTE o JSON válido, sem markdown."""

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 900,
            "response_format": {"type": "json_object"},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return json.loads(resp.json()["choices"][0]["message"]["content"].strip())


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",  type=int,          help="N produtos sem atributos")
    parser.add_argument("--all",    action="store_true", help="Todos sem atributos")
    parser.add_argument("--id",     type=int,          help="Produto específico pelo ID")
    parser.add_argument("--rerun",  action="store_true", help="Re-processa já enriquecidos")
    parser.add_argument("--delay",  type=float, default=2.0)
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
            atributos = {k: v for k, v in result.get("atributos", {}).items() if k != "_desc"}

            save_enrichment(p["id"], specs, atributos)

            filled = {k: v for k, v in atributos.items()
                      if v not in (None, [], "", False) and k != "obs"}
            print(f"  ✓ {len(filled)} atributos preenchidos: {list(filled.keys())}")
            ok += 1
        except Exception as e:
            print(f"  ✗ Erro: {e}")
            err += 1

        if i < len(products):
            time.sleep(args.delay)

    print(f"\n✅ {ok} enriquecidos | ❌ {err} erros\n")


if __name__ == "__main__":
    main()
