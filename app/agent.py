import os
from typing import Annotated
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from app.tools.tray_tools import (
    search_products,
    get_product_details,
    list_categories,
    search_products_by_category,
    get_order_status,
)

load_dotenv()

TOOLS = [
    search_products,
    get_product_details,
    list_categories,
    search_products_by_category,
    get_order_status,
]

SYSTEM_PROMPT = """Você é a assistente virtual da OutletSIM, uma loja outlet com mais de 70.000 produtos:
tecnologia, eletrônicos, informática, equipamentos industriais, moda, alimentos e muito mais.

Seu papel é ajudar clientes a encontrar produtos, consultar preços/estoque e rastrear pedidos.
Responda sempre em português. Seja direta e objetiva.

## Regras de uso das ferramentas

1. **Busca por palavra-chave** → use `search_products(query)`.
   Exemplos: "notebook", "impressora", "tênis nike", "cabo hdmi".

2. **Navegar por categoria**:
   - SEMPRE chame `list_categories()` primeiro para obter a lista com IDs numéricos.
   - Em seguida chame `search_products_by_category(category_id=<ID_NUMÉRICO>)`.
   - NUNCA invente ou adivinhe um ID de categoria. Use APENAS os IDs retornados por list_categories.

3. **Detalhes de produto** → use `get_product_details(product_id)` com o ID numérico do produto.

4. **Status de pedido** → use `get_order_status(order_id)`.

## Ao apresentar resultados
- Mostre nome, preço e estoque.
- Se estoque = 0, informe que está indisponível no momento.
- Se não encontrar nada, sugira uma busca alternativa por palavra-chave.

## Fora do escopo
Para trocas, devoluções ou suporte técnico complexo, oriente o cliente a acessar o SAC pelo site."""


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
