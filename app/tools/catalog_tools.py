from langchain_core.tools import tool
from app import db


@tool
def buscar_catalogo(query: str) -> str:
    """Busca produtos no estoque outlet da OutletSIM por nome, modelo, categoria ou característica.
    Use quando o cliente perguntar sobre disponibilidade ou preço de qualquer produto do estoque físico.
    Exemplos: 'HD SAS 600GB', 'firewall Sophos', 'memória DDR3 8GB', 'bodycam', 'telefone Avaya'.
    """
    results = db.search_catalog(query)
    if not results:
        return f"Nenhum produto encontrado no estoque para '{query}'."

    linhas = [f"Produtos encontrados para '{query}':\n"]
    for p in results:
        preco = f"R${p['preco_venda']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        linha = f"• [{p['categoria']}] {p['titulo']} | Estoque: {p['qtd']} un. | Preço: {preco}"
        if p.get("descricao"):
            linha += f"\n  ↳ {p['descricao']}"
        linhas.append(linha)

    return "\n".join(linhas)


@tool
def listar_categorias_catalogo() -> str:
    """Lista todas as categorias de produtos disponíveis no estoque outlet da OutletSIM."""
    cats = db.get_catalog_categories()
    if not cats:
        return "Nenhuma categoria disponível no momento."
    return "Categorias no estoque outlet:\n" + "\n".join(f"• {c}" for c in cats)
