from langchain_core.tools import tool
from app.tray import client


@tool
def search_products(query: str, limit: int = 10) -> str:
    """Busca produtos na loja por nome ou palavra-chave livre.
    Use para qualquer pergunta sobre produtos, preços ou disponibilidade."""
    data = client.get("/search", {"query": query, "limit": limit, "available": 1})
    products = data.get("Products", [])
    if not products:
        return f"Nenhum produto encontrado para '{query}'."
    total = data.get("paging", {}).get("total", len(products))
    lines = [f"{total} produto(s) encontrado(s) para '{query}':\n"]
    for item in products:
        p = item["Product"]
        promo = p.get("promotional_price", "0")
        price = promo if float(promo or 0) > 0 else p.get("price", "N/A")
        lines.append(f"• [{p['id']}] {p['name']} — R$ {price} | Estoque: {p.get('stock', 0)}")
    return "\n".join(lines)


@tool
def get_product_details(product_id: int) -> str:
    """Retorna detalhes completos de um produto: descrição, preço, estoque, marca, variações.
    Use quando o cliente quiser saber mais sobre um produto específico pelo ID."""
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
    """Lista as categorias de produtos disponíveis na loja.
    Use quando o cliente quiser navegar por categoria ou perguntar o que a loja vende."""
    data = client.get("/categories", {"limit": 100, "active": 1, "has_product": 1})
    cats = data.get("Categories", [])
    if not cats:
        return "Nenhuma categoria encontrada."
    lines = ["Categorias disponíveis:\n"]
    for item in cats:
        c = item.get("Category", item)
        name = c.get("name", "").strip()
        if name and not name.isdigit() and len(name) > 2:
            lines.append(f"• {name}")
    return "\n".join(lines)


@tool
def search_products_by_category(category_name: str, limit: int = 10) -> str:
    """Busca produtos de uma categoria pelo nome (ex: 'LINHA PRIME', 'Talheres').
    Use quando o cliente escolher uma categoria. Passa o nome como apareceu na lista."""
    data = client.get("/categories", {"limit": 100, "active": 1, "has_product": 1})
    cats = [item.get("Category", item) for item in data.get("Categories", [])]
    query = category_name.lower().strip()
    match = next((c for c in cats if query in c.get("name", "").lower() or c.get("name", "").lower() in query), None)
    if not match:
        return f"Categoria '{category_name}' não encontrada. Use list_categories para ver as opções."
    prods = client.get("/products", {"category_id": match["id"], "available": 1, "limit": limit, "order": "price"})
    products = prods.get("Products", [])
    total = prods.get("paging", {}).get("total", 0)
    if not products:
        return f"Nenhum produto disponível em '{match['name']}' no momento."
    lines = [f"Produtos em '{match['name']}' ({total} total):\n"]
    for item in products:
        p = item["Product"]
        promo = p.get("promotional_price", "0")
        price = promo if float(promo or 0) > 0 else p.get("price", "N/A")
        lines.append(f"• [{p['id']}] {p['name']} — R$ {price} | Estoque: {p.get('stock', 0)}")
    return "\n".join(lines)


@tool
def get_best_sellers(limit: int = 10) -> str:
    """Lista os produtos mais vendidos da loja.
    Use quando o cliente perguntar sobre produtos populares, mais vendidos ou recomendações."""
    data = client.get("/products", {"available": 1, "limit": limit, "order": "quantity_sold"})
    products = data.get("Products", [])
    if not products:
        return "Não foi possível carregar os mais vendidos."
    lines = ["Produtos mais vendidos:\n"]
    for i, item in enumerate(products, 1):
        p = item["Product"]
        promo = p.get("promotional_price", "0")
        price = promo if float(promo or 0) > 0 else p.get("price", "N/A")
        sold = p.get("quantity_sold", 0)
        lines.append(f"{i}. [{p['id']}] {p['name']} — R$ {price} | Vendidos: {sold}")
    return "\n".join(lines)


@tool
def search_products_by_brand(brand_name: str, limit: int = 10) -> str:
    """Busca produtos de uma marca específica (ex: 'Samsung', 'Intelbras', 'Nike').
    Use quando o cliente perguntar por produtos de uma marca."""
    data = client.get("/brands", {"limit": 100})
    brands = data.get("Brands", [])
    query = brand_name.lower().strip()
    match = next(
        (b.get("Brand", b) for b in brands
         if query in (b.get("Brand", b).get("name") or b.get("Brand", b).get("brand", "")).lower()),
        None
    )
    if match:
        match = {**match, "name": match.get("name") or match.get("brand", "")}
    if not match:
        return f"Marca '{brand_name}' não encontrada no catálogo."
    prods = client.get("/products", {"brand_id": match["id"], "available": 1, "limit": limit, "order": "price"})
    products = prods.get("Products", [])
    total = prods.get("paging", {}).get("total", 0)
    if not products:
        return f"Nenhum produto disponível da marca '{match['name']}' no momento."
    lines = [f"Produtos da marca '{match['name']}' ({total} total):\n"]
    for item in products:
        p = item["Product"]
        promo = p.get("promotional_price", "0")
        price = promo if float(promo or 0) > 0 else p.get("price", "N/A")
        lines.append(f"• [{p['id']}] {p['name']} — R$ {price} | Estoque: {p.get('stock', 0)}")
    return "\n".join(lines)


@tool
def list_brands() -> str:
    """Lista todas as marcas disponíveis na loja.
    Use quando o cliente perguntar quais marcas a loja trabalha."""
    data = client.get("/brands", {"limit": 100})
    brands = data.get("Brands", [])
    if not brands:
        return "Nenhuma marca encontrada."
    names = []
    for b in brands:
        br = b.get("Brand", b)
        name = br.get("name") or br.get("brand", "")
        if name:
            names.append(name)
    return "Marcas disponíveis:\n" + "\n".join(f"• {n}" for n in sorted(names))
