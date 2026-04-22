from langchain_core.tools import tool
from app.tray import client


@tool
def search_products(query: str, limit: int = 10) -> str:
    """Busca produtos na loja OutletSIM por nome ou palavra-chave.
    Use quando o cliente perguntar sobre produtos, preços ou disponibilidade."""
    data = client.get("/search", {
        "query": query,
        "limit": limit,
        "available": 1,
    })
    products = data.get("Products", [])
    if not products:
        return "Nenhum produto encontrado para essa busca."

    total = data.get("paging", {}).get("total", len(products))
    lines = [f"Encontrei {total} produto(s) para '{query}'. Mostrando os primeiros {len(products)}:\n"]
    for item in products:
        p = item["Product"]
        promo = p.get("promotional_price", "0")
        price = promo if float(promo or 0) > 0 else p.get("price", "N/A")
        stock = p.get("stock", 0)
        lines.append(
            f"• [{p['id']}] {p['name']}\n"
            f"  Preço: R$ {price}  |  Estoque: {stock}"
        )
    return "\n".join(lines)


@tool
def get_product_details(product_id: int) -> str:
    """Retorna detalhes completos de um produto pelo ID, incluindo descrição, variações e estoque.
    Use quando o cliente quiser saber mais sobre um produto específico."""
    data = client.get(f"/products/{product_id}")
    p = data.get("Product")
    if not p:
        return "Produto não encontrado."

    promo = p.get("promotional_price", "0")
    price = promo if float(promo or 0) > 0 else p.get("price", "N/A")
    lines = [
        f"**{p['name']}**",
        f"ID: {p['id']}",
        f"Preço: R$ {price}",
        f"Estoque: {p.get('stock', 0)}",
        f"Disponível: {'Sim' if p.get('available') == '1' else 'Não'}",
        f"Marca: {p.get('brand', 'N/A')}",
        f"Modelo: {p.get('model', 'N/A')}",
        f"Garantia: {p.get('warranty', 'N/A')}",
        f"Peso: {p.get('weight', 'N/A')} kg",
    ]
    if p.get("description"):
        desc = p["description"][:500].strip()
        lines.append(f"\nDescrição: {desc}{'...' if len(p['description']) > 500 else ''}")

    variants = p.get("Variants", [])
    if variants:
        lines.append(f"\nVariações ({len(variants)}):")
        for v in variants[:5]:
            var = v.get("Variant", v)
            lines.append(f"  • {var.get('VariantValue', {}).get('name', '')} — estoque: {var.get('stock', 0)}, preço: R$ {var.get('price', 'N/A')}")

    return "\n".join(lines)


def _get_categories() -> list[dict]:
    data = client.get("/categories", {"limit": 100, "active": 1, "has_product": 1})
    result = []
    for item in data.get("Categories", []):
        c = item.get("Category", item)
        name = c.get("name", "").strip()
        if name and not name.isdigit() and len(name) > 2:
            result.append({"id": c["id"], "name": name})
    return result


def _format_products(products: list, total: int) -> str:
    lines = [f"{total} produto(s) encontrado(s):\n"]
    for item in products:
        p = item["Product"]
        promo = p.get("promotional_price", "0")
        price = promo if float(promo or 0) > 0 else p.get("price", "N/A")
        stock = p.get("stock", 0)
        lines.append(f"• [{p['id']}] {p['name']} — R$ {price} | Estoque: {stock}")
    return "\n".join(lines)


@tool
def list_categories() -> str:
    """Lista as categorias de produtos disponíveis na loja.
    Use quando o cliente quiser saber o que a loja tem ou navegar por categoria."""
    cats = _get_categories()
    if not cats:
        return "Nenhuma categoria encontrada."
    lines = ["Categorias disponíveis na OutletSIM:\n"]
    for c in cats:
        lines.append(f"• {c['name']}")
    return "\n".join(lines)


@tool
def search_products_by_category(category_name: str, limit: int = 10) -> str:
    """Busca produtos de uma categoria pelo NOME da categoria (ex: 'ROUPAS MASCULINAS', 'Alimentos').
    Use quando o cliente escolher uma categoria da lista. Passe o nome exato como apareceu na lista."""
    cats = _get_categories()
    # Busca case-insensitive e por substring
    query = category_name.lower().strip()
    match = next(
        (c for c in cats if query in c["name"].lower() or c["name"].lower() in query),
        None
    )
    if not match:
        names = ", ".join(c["name"] for c in cats[:8])
        return f"Categoria '{category_name}' não encontrada. Categorias disponíveis: {names}..."

    data = client.get("/products", {
        "category_id": match["id"],
        "available": 1,
        "limit": limit,
        "order": "price",
    })
    products = data.get("Products", [])
    total = data.get("paging", {}).get("total", 0)
    if not products:
        return f"Nenhum produto disponível na categoria '{match['name']}' no momento."

    return f"Produtos em '{match['name']}':\n\n" + _format_products(products, total)


@tool
def get_order_status(order_id: int) -> str:
    """Consulta o status de um pedido pelo número do pedido.
    Use quando o cliente quiser saber onde está o pedido ou o status da entrega."""
    data = client.get(f"/orders/{order_id}")
    order = data.get("Order")
    if not order:
        return "Pedido não encontrado. Verifique o número informado."

    status_map = {
        "0": "Aguardando pagamento",
        "1": "Pagamento aprovado",
        "2": "Em separação",
        "3": "Nota fiscal emitida",
        "4": "Enviado",
        "5": "Entregue",
        "6": "Cancelado",
        "7": "Troca/Devolução",
    }
    status_code = str(order.get("status", ""))
    status = status_map.get(status_code, f"Status {status_code}")

    lines = [
        f"**Pedido #{order['id']}**",
        f"Status: {status}",
        f"Data: {order.get('date', 'N/A')}",
        f"Total: R$ {order.get('total', 'N/A')}",
        f"Frete: R$ {order.get('shipment_value', 'N/A')}",
        f"Forma de pagamento: {order.get('payment_method_name', 'N/A')}",
    ]
    if order.get("shipment_alias"):
        lines.append(f"Transportadora: {order['shipment_alias']}")
    if order.get("sending_code"):
        lines.append(f"Código de rastreio: {order['sending_code']}")

    return "\n".join(lines)
