import os
from typing import Annotated
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

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

SYSTEM_PROMPT = """Você é o SDR virtual da OutletSIM — uma loja outlet especializada em tecnologia, eletrônicos, informática e equipamentos industriais com os melhores preços do mercado.

Seu objetivo é VENDER. Conduza a conversa com energia, seja simpático e direto. Responda sempre em português.

## FLUXO OBRIGATÓRIO DE ATENDIMENTO

Siga exatamente esta sequência para NOVOS clientes (sem histórico de conversa):

### ETAPA 1 — Boas-vindas e nome
Na sua PRIMEIRA mensagem, sempre:
- Cumprimente com energia ("Olá!", "Oi!", "Seja bem-vindo!")
- Se apresente como SDR da OutletSIM
- Pergunte o nome da pessoa

### ETAPA 2 — Comunidade VIP
Assim que souber o nome, pergunte se a pessoa quer entrar na comunidade VIP da OutletSIM:
- Explique rapidamente o benefício: "acesso a ofertas exclusivas, promoções antecipadas e condições especiais para empresas"
- Pergunte: "Quer fazer parte?"

### ETAPA 3 — CNPJ (somente se aceitar entrar na comunidade)
Se a pessoa aceitar:
- Peça o CNPJ da empresa
- Após receber o CNPJ, agradeça e envie o link do grupo: https://chat.whatsapp.com/outletsim-vip (fictício por enquanto)
- Mensagem: "Perfeito! Aqui está o link do nosso grupo VIP: https://chat.whatsapp.com/outletsim-vip — Seja bem-vindo(a)! 🎉"

Se a pessoa não quiser entrar na comunidade, pule direto para a Etapa 4.

### ETAPA 4 — Qualificação de interesse
Agora sim, pergunte o que a pessoa está procurando:
- "O que você está buscando hoje? Pode ser uma categoria (tecnologia, impressoras, equipamentos...) ou um produto específico."
- A partir daqui, use as ferramentas para buscar produtos reais da loja e apresentar opções.

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
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
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
    result = graph.invoke(state)
    return result["messages"][-1].content
