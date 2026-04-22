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


@tool
def list_categories() -> str:
    """Lista as categorias de produtos disponíveis na loja com seus IDs.
    SEMPRE use esta tool antes de search_products_by_category para obter o ID correto da categoria.
    Use quando o cliente quiser navegar por categoria ou perguntar o que a loja vende."""
    data = client.get("/categories", {"limit": 100, "active": 1, "has_product": 1})
    cats = data.get("Categories", [])
    if not cats:
        return "Nenhuma categoria encontrada."
    lines = ["Categorias disponíveis (use o ID numérico para buscar produtos):\n"]
    for item in cats:
        c = item.get("Category", item)
        # Filtra nomes que parecem IDs ou lixo de dados de teste
        name = c.get("name", "").strip()
        if name and not name.isdigit() and len(name) > 2:
            lines.append(f"• ID={c['id']} | {name}")
    return "\n".join(lines)


@tool
def search_products_by_category(category_id: int, limit: int = 10) -> str:
    """Busca produtos disponíveis de uma categoria pelo ID numérico da categoria.
    IMPORTANTE: use o ID numérico retornado por list_categories, nunca o nome.
    Use quando o cliente quiser ver produtos de uma categoria em particular."""
    data = client.get("/products", {
        "category_id": category_id,
        "available": 1,
        "limit": limit,
        "order": "price",
    })
    products = data.get("Products", [])
    total = data.get("paging", {}).get("total", 0)
    if not products:
        return f"Nenhum produto disponível nessa categoria (ID {category_id}). Tente outra categoria."

    lines = [f"{total} produto(s) disponíveis nessa categoria:\n"]
    for item in products:
        p = item["Product"]
        promo = p.get("promotional_price", "0")
        price = promo if float(promo or 0) > 0 else p.get("price", "N/A")
        stock = p.get("stock", 0)
        lines.append(f"• [{p['id']}] {p['name']} — R$ {price} | Estoque: {stock}")
    return "\n".join(lines)


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
