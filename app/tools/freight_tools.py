from langchain_core.tools import tool
from app.tray import client


@tool
def calculate_freight(zip_code: str, product_id: int, quantity: int = 1) -> str:
    """Calcula o frete para um produto até um CEP específico.
    Use quando o cliente perguntar quanto custa o frete ou prazo de entrega.
    Parâmetros: zip_code (CEP do destino, só números), product_id (ID do produto), quantity."""
    zip_clean = zip_code.replace("-", "").replace(".", "").strip()
    data = client.get("/freight/calculate", {
        "zip_code": zip_clean,
        "products[0][product_id]": product_id,
        "products[0][quantity]": quantity,
    })
    freights = data.get("Freights", [])
    if not freights:
        error = data.get("message") or data.get("name") or "Não foi possível calcular o frete para este CEP."
        return f"Frete não disponível: {error}"
    lines = [f"Opções de frete para o CEP {zip_code}:\n"]
    for item in freights:
        f = item.get("Freight", item)
        lines.append(
            f"• {f.get('carrier', 'N/A')} — {f.get('modality', '')}\n"
            f"  Valor: R$ {f.get('value', 'N/A')} | Prazo: {f.get('delivery_time', 'N/A')} dia(s)"
        )
    return "\n".join(lines)


@tool
def list_freight_methods() -> str:
    """Lista os métodos de entrega configurados na loja.
    Use quando o cliente quiser saber quais transportadoras ou opções de envio estão disponíveis."""
    data = client.get("/freight/methods", {"limit": 20})
    methods = data.get("FreightMethods", [])
    if not methods:
        return "Nenhum método de frete configurado."
    lines = ["Métodos de entrega disponíveis:\n"]
    for item in methods:
        m = item.get("FreightMethod", item)
        active = "✅" if m.get("active") == "1" else "❌"
        lines.append(f"{active} {m.get('name', 'N/A')} — {m.get('type', '')}")
    return "\n".join(lines)
