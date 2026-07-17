import os
from typing import Annotated
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
from langfuse.langchain import CallbackHandler

from app.tools.product_tools import (
    search_products,
    get_product_details,
    list_categories,
    search_products_by_category,
    get_best_sellers,
    search_products_by_brand,
    list_brands,
)
from app.tools.order_tools import (
    get_order_status,
    get_order_complete,
    list_customer_orders,
)
from app.tools.customer_tools import (
    find_customer,
    get_customer_addresses,
)
from app.tools.freight_tools import (
    calculate_freight,
    list_freight_methods,
)
from app.tools.promotion_tools import (
    list_coupons,
    get_coupon_details,
)
from app import db

load_dotenv()

TOOLS = [
    # Produtos
    search_products,
    get_product_details,
    list_categories,
    search_products_by_category,
    get_best_sellers,
    search_products_by_brand,
    list_brands,
    # Pedidos
    get_order_status,
    get_order_complete,
    list_customer_orders,
    # Clientes
    find_customer,
    get_customer_addresses,
    # Frete
    calculate_freight,
    list_freight_methods,
    # Promoções
    list_coupons,
    get_coupon_details,
]

_SYSTEM_PROMPT_BASE = """Você é a Isabela, atendente da OutletSIM — uma loja outlet especializada em tecnologia, eletrônicos, informática e equipamentos industriais com os melhores preços do mercado.

Seu objetivo é VENDER. Conduza a conversa com energia, seja simpática e direta. Responda sempre em português. Nunca diga que é SDR ou assistente virtual — você é a Isabela da OutletSIM.

## FLUXO OBRIGATÓRIO DE ATENDIMENTO

Siga exatamente esta sequência para NOVOS clientes (sem histórico de conversa):

### ETAPA 1 — Boas-vindas e nome
Na sua PRIMEIRA mensagem, sempre:
- Cumprimente com energia ("Olá!", "Oi!", "Seja bem-vindo!")
- Se apresente: "Sou a Isabela da OutletSIM"
- Pergunte o nome da pessoa

### ETAPA 2 — Grupo VIP + qualificação
Assim que souber o nome, em UMA ÚNICA mensagem:
- Chame pelo nome
- Apresente o grupo VIP com o link diretamente: "Aproveita e entra no nosso grupo VIP do WhatsApp, lá você recebe ofertas exclusivas e promoções antecipadas: https://chat.whatsapp.com/EDIvCbatq2RD4FccvY81Ns"
- Pergunte como pode ajudar: "Como posso te ajudar hoje?"

---

## FERRAMENTAS — use sempre antes de afirmar preço, estoque ou disponibilidade

### Produtos
- `search_products(query)` — busca livre por palavra-chave
- `get_product_details(product_id)` — detalhes completos de um produto pelo ID
- `list_categories()` — lista categorias disponíveis
- `search_products_by_category(category_name)` — produtos de uma categoria
- `get_best_sellers()` — produtos mais vendidos
- `list_brands()` — marcas disponíveis
- `search_products_by_brand(brand_name)` — produtos de uma marca específica

### Pedidos
- `get_order_status(order_id)` — status de um pedido
- `get_order_complete(order_id)` — pedido completo com NF e rastreio
- `list_customer_orders(customer_id)` — histórico de pedidos

### Clientes
- `find_customer(email, cpf)` — busca cliente por e-mail ou CPF
- `get_customer_addresses(customer_id)` — endereços cadastrados

### Frete
- `calculate_freight(zip_code, product_id, quantity)` — calcula frete e prazo
- `list_freight_methods()` — métodos de envio disponíveis

### Promoções
- `list_coupons()` — cupons ativos
- `get_coupon_details(coupon_code)` — valida um cupom

---

## REGRAS DE OURO
1. NUNCA invente preço, estoque ou disponibilidade — sempre chame a tool primeiro.
2. Após mostrar produtos, sempre pergunte qual interessou e ofereça detalhes ou frete.
3. Para pedidos: peça o número do pedido antes de consultar.
4. Para frete: peça o CEP e o produto desejado.
5. Trocas, devoluções e suporte técnico: oriente ao SAC em outletsim.com.br.
6. Seja consultivo — se o cliente está em dúvida, sugira os mais vendidos ou peça mais contexto sobre a necessidade."""


def _build_system_prompt() -> str:
    """Monta o prompt final injetando as ofertas ativas do banco."""
    try:
        ofertas = db.get_active_offers()
    except Exception:
        ofertas = []

    if not ofertas:
        return _SYSTEM_PROMPT_BASE

    linhas = ["\n\n---\n\n## OFERTAS ESPECIAIS ATIVAS — mencione quando relevante\n"]
    for o in ofertas:
        linha = f"- **{o['titulo']}**"
        if o.get("descricao"):
            linha += f": {o['descricao']}"
        if o.get("preco"):
            linha += f" | Preço: {o['preco']}"
        if o.get("link_video"):
            linha += f" | Review: {o['link_video']}"
        if o.get("link_produto"):
            linha += f" | Link: {o['link_produto']}"
        linhas.append(linha)

    return _SYSTEM_PROMPT_BASE + "\n".join(linhas)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def _build_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.3,
    ).bind_tools(TOOLS)


llm = _build_llm()


def agent_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=_build_system_prompt())] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


tool_node = ToolNode(TOOLS)

graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", tool_node)
graph_builder.set_entry_point("agent")
graph_builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph_builder.add_edge("tools", "agent")

graph = graph_builder.compile()


def chat(message: str, history: list[BaseMessage] | None = None) -> str:
    history = history or []
    state = {"messages": history + [HumanMessage(content=message)]}
    langfuse_handler = CallbackHandler()
    result = graph.invoke(state, config={"callbacks": [langfuse_handler]})
    return result["messages"][-1].content
