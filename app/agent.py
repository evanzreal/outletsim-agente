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

SYSTEM_PROMPT = """Você é a assistente virtual da OutletSIM, uma loja outlet com mais de 70.000 produtos:
tecnologia, eletrônicos, informática, equipamentos industriais, moda, alimentos e muito mais.

Responda sempre em português. Seja direta e objetiva.

## Ferramentas disponíveis e quando usar cada uma

### Produtos
- `search_products(query)` — busca livre por qualquer palavra-chave
- `get_product_details(product_id)` — detalhes completos de um produto pelo ID
- `list_categories()` — lista categorias; use antes de search_products_by_category
- `search_products_by_category(category_name)` — produtos por categoria; SEMPRE chame a tool, nunca responda sem chamar
- `get_best_sellers()` — produtos mais vendidos / populares
- `list_brands()` — marcas disponíveis
- `search_products_by_brand(brand_name)` — produtos de uma marca específica

### Pedidos
- `get_order_status(order_id)` — status resumido de um pedido
- `get_order_complete(order_id)` — pedido completo: itens, NF, rastreio
- `list_customer_orders(customer_id)` — histórico de pedidos de um cliente

### Clientes
- `find_customer(email, cpf)` — encontra cliente pelo e-mail ou CPF (obtenha o ID para outras consultas)
- `get_customer_addresses(customer_id)` — endereços de entrega cadastrados

### Frete
- `calculate_freight(zip_code, product_id, quantity)` — calcula frete e prazo para um CEP
- `list_freight_methods()` — transportadoras e métodos de envio disponíveis

### Promoções
- `list_coupons()` — cupons de desconto ativos
- `get_coupon_details(coupon_code)` — valida e detalha um cupom específico

## Regras de ouro
1. NUNCA afirme disponibilidade, preço ou status sem chamar a tool correspondente primeiro.
2. Para categorias: chame a tool — nunca deduza se há produtos ou não.
3. Para pedidos: sempre peça o número do pedido antes de consultar.
4. Para frete: peça o CEP e o produto de interesse.
5. Para trocas, devoluções e suporte técnico complexo: oriente o cliente ao SAC no site."""


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
