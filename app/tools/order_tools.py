from langchain_core.tools import tool
from app.tray import client

STATUS_MAP = {
    "0": "Aguardando pagamento",
    "1": "Pagamento aprovado",
    "2": "Em separação",
    "3": "Nota fiscal emitida",
    "4": "Enviado",
    "5": "Entregue",
    "6": "Cancelado",
    "7": "Troca/Devolução",
}


@tool
def get_order_status(order_id: int) -> str:
    """Consulta status básico de um pedido pelo número.
    Use quando o cliente quiser saber onde está o pedido."""
    data = client.get(f"/orders/{order_id}")
    order = data.get("Order")
    if not order:
        return "Pedido não encontrado. Verifique o número informado."
    status = STATUS_MAP.get(str(order.get("status", "")), f"Status {order.get('status')}")
    lines = [
        f"**Pedido #{order['id']}**",
        f"Status: {status}",
        f"Data: {order.get('date', 'N/A')}",
        f"Total: R$ {order.get('total', 'N/A')}",
        f"Frete: R$ {order.get('shipment_value', 'N/A')}",
        f"Pagamento: {order.get('payment_method_name', 'N/A')}",
    ]
    if order.get("shipment_alias"):
        lines.append(f"Transportadora: {order['shipment_alias']}")
    if order.get("sending_code"):
        lines.append(f"Rastreio: {order['sending_code']}")
    return "\n".join(lines)


@tool
def get_order_complete(order_id: int) -> str:
    """Retorna o pedido completo com todos os itens, valores, NF e rastreio.
    Use quando o cliente quiser detalhes completos do pedido (itens comprados, NF, etc)."""
    data = client.get(f"/orders/{order_id}/complete")
    order = data.get("Order")
    if not order:
        return "Pedido não encontrado."
    status = STATUS_MAP.get(str(order.get("status", "")), f"Status {order.get('status')}")
    lines = [
        f"**Pedido #{order['id']}** — {status}",
        f"Data: {order.get('date', 'N/A')}",
        f"Total: R$ {order.get('total', 'N/A')} | Frete: R$ {order.get('shipment_value', 'N/A')}",
        f"Pagamento: {order.get('payment_method_name', 'N/A')}",
    ]
    if order.get("sending_code"):
        lines.append(f"Código de rastreio: {order['sending_code']}")
    products = order.get("ProductsSold", [])
    if products:
        lines.append(f"\nItens do pedido ({len(products)}):")
        for item in products:
            p = item.get("ProductsSold", item)
            lines.append(f"  • {p.get('name', 'N/A')} — {p.get('quantity', 1)}x R$ {p.get('price', 'N/A')}")
    nf = order.get("Invoice")
    if nf:
        lines.append(f"\nNota Fiscal: {nf.get('cnpj', 'N/A')} | Chave: {nf.get('key', 'N/A')}")
    return "\n".join(lines)


@tool
def list_customer_orders(customer_id: int, limit: int = 5) -> str:
    """Lista os pedidos de um cliente pelo ID do cliente.
    Use quando o cliente quiser ver o histórico de compras."""
    data = client.get("/orders", {"customer_id": customer_id, "limit": limit, "order": "date", "sort": "desc"})
    orders = data.get("Orders", [])
    if not orders:
        return "Nenhum pedido encontrado para este cliente."
    total = data.get("paging", {}).get("total", len(orders))
    lines = [f"{total} pedido(s) encontrado(s):\n"]
    for item in orders:
        o = item.get("Order", item)
        status = STATUS_MAP.get(str(o.get("status", "")), "—")
        lines.append(f"• Pedido #{o['id']} | {o.get('date','')[:10]} | R$ {o.get('total','N/A')} | {status}")
    return "\n".join(lines)
