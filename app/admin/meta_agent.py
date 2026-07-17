import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from app import db

SYSTEM_PROMPT = """Você é o assistente admin da OutletSIM.
Você ajuda o dono da loja a gerenciar as ofertas especiais que a Isabela (agente de vendas) vai mencionar para os clientes.

Você pode:
- Listar as ofertas ativas
- Adicionar novas ofertas (produto, descrição, preço, link de vídeo/review, link do produto)
- Remover ofertas que já acabaram
- Atualizar informações de uma oferta existente

Sempre confirme o que foi feito após cada ação. Se o dono pedir para adicionar uma oferta, extraia as informações da mensagem e chame a ferramenta diretamente — não peça confirmação antes, só depois.

Responda sempre em português."""


@tool
def listar_ofertas() -> str:
    """Lista todas as ofertas especiais ativas no momento."""
    ofertas = db.get_active_offers()
    if not ofertas:
        return "Nenhuma oferta ativa no momento."
    linhas = ["Ofertas ativas:\n"]
    for o in ofertas:
        linhas.append(f"[ID {o['id']}] {o['titulo']}")
        if o.get("descricao"):
            linhas.append(f"  Descrição: {o['descricao']}")
        if o.get("preco"):
            linhas.append(f"  Preço: {o['preco']}")
        if o.get("link_video"):
            linhas.append(f"  Review: {o['link_video']}")
        if o.get("link_produto"):
            linhas.append(f"  Link: {o['link_produto']}")
        linhas.append("")
    return "\n".join(linhas)


@tool
def adicionar_oferta(
    titulo: str,
    descricao: str = "",
    preco: str = "",
    link_video: str = "",
    link_produto: str = "",
    expira_em: str = "",
) -> str:
    """
    Adiciona uma nova oferta especial. Parâmetros:
    - titulo: nome do produto (obrigatório)
    - descricao: especificações ou detalhes
    - preco: preço formatado, ex: "R$2.499 ou 12x R$224"
    - link_video: URL do review no YouTube
    - link_produto: URL do produto no site
    - expira_em: data de expiração no formato "YYYY-MM-DD" (opcional)
    """
    oferta_id = db.add_offer(
        titulo=titulo,
        descricao=descricao or None,
        preco=preco or None,
        link_video=link_video or None,
        link_produto=link_produto or None,
        expira_em=expira_em or None,
    )
    return f"Oferta '{titulo}' adicionada com sucesso! ID: {oferta_id}"


@tool
def remover_oferta(oferta_id: int) -> str:
    """Remove (desativa) uma oferta pelo ID. Use listar_ofertas para ver os IDs."""
    ok = db.deactivate_offer(oferta_id)
    if ok:
        return f"Oferta ID {oferta_id} removida com sucesso."
    return f"Oferta ID {oferta_id} não encontrada."


@tool
def atualizar_oferta(oferta_id: int, campo: str, valor: str) -> str:
    """
    Atualiza um campo de uma oferta existente. Campos permitidos:
    titulo, descricao, preco, link_video, link_produto, expira_em.
    Exemplo: atualizar_oferta(1, "preco", "R$1.999")
    """
    campos_validos = {"titulo", "descricao", "preco", "link_video", "link_produto", "expira_em"}
    if campo not in campos_validos:
        return f"Campo '{campo}' inválido. Use: {', '.join(campos_validos)}"
    ok = db.update_offer(oferta_id, **{campo: valor})
    if ok:
        return f"Oferta ID {oferta_id} atualizada: {campo} = '{valor}'"
    return f"Oferta ID {oferta_id} não encontrada."


TOOLS = [listar_ofertas, adicionar_oferta, remover_oferta, atualizar_oferta]

_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder("history"),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

_llm = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0.2,
)

_agent = create_openai_tools_agent(_llm, TOOLS, _prompt)
_executor = AgentExecutor(agent=_agent, tools=TOOLS, verbose=False)


def chat(message: str, history: list[dict] | None = None) -> str:
    lc_history = []
    for m in (history or []):
        if m["role"] == "user":
            lc_history.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_history.append(AIMessage(content=m["content"]))

    result = _executor.invoke({"input": message, "history": lc_history})
    return result["output"]
