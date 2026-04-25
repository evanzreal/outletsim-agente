from langchain_core.tools import tool
from app.tray import client


@tool
def list_coupons() -> str:
    """Lista os cupons de desconto ativos na loja.
    Use quando o cliente perguntar se há cupons, promoções ou descontos disponíveis."""
    data = client.get("/coupons", {"limit": 20, "active": 1})
    coupons = data.get("Coupons", [])
    if not coupons:
        return "Nenhum cupom ativo no momento."
    lines = ["Cupons disponíveis:\n"]
    for item in coupons:
        c = item.get("Coupon", item)
        discount = (
            f"{c.get('discount_value', '')}%" if c.get("type") == "percent"
            else f"R$ {c.get('discount_value', '')}"
        )
        validity = c.get("date_end", "")
        lines.append(
            f"• **{c.get('code', 'N/A')}** — {discount} de desconto"
            + (f" | Válido até {validity[:10]}" if validity and validity != "0000-00-00" else "")
            + (f" | Mín. R$ {c.get('minimum_value', '0')}" if float(c.get("minimum_value", 0) or 0) > 0 else "")
        )
    return "\n".join(lines)


@tool
def get_coupon_details(coupon_code: str) -> str:
    """Retorna os detalhes de um cupom específico pelo código.
    Use quando o cliente informar um código de cupom e quiser saber se é válido."""
    data = client.get("/coupons", {"code": coupon_code, "limit": 1})
    coupons = data.get("Coupons", [])
    if not coupons:
        return f"Cupom '{coupon_code}' não encontrado ou inválido."
    c = coupons[0].get("Coupon", coupons[0])
    active = c.get("active") == "1"
    discount = (
        f"{c.get('discount_value', '')}%" if c.get("type") == "percent"
        else f"R$ {c.get('discount_value', '')}"
    )
    lines = [
        f"**Cupom: {c.get('code')}**",
        f"Status: {'✅ Ativo' if active else '❌ Inativo'}",
        f"Desconto: {discount}",
        f"Tipo: {'Percentual' if c.get('type') == 'percent' else 'Valor fixo'}",
    ]
    if float(c.get("minimum_value", 0) or 0) > 0:
        lines.append(f"Pedido mínimo: R$ {c.get('minimum_value')}")
    if c.get("date_end") and c["date_end"] != "0000-00-00":
        lines.append(f"Válido até: {c['date_end'][:10]}")
    if c.get("uses_customer"):
        lines.append(f"Uso por cliente: {c.get('uses_customer')}x")
    return "\n".join(lines)
