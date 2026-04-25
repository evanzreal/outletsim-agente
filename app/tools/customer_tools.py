from langchain_core.tools import tool
from app.tray import client


@tool
def find_customer(email: str = "", cpf: str = "") -> str:
    """Busca um cliente pelo e-mail ou CPF.
    Use para identificar o cliente antes de consultar pedidos ou endereços.
    Passe email OU cpf (ao menos um)."""
    if not email and not cpf:
        return "Informe o e-mail ou CPF do cliente para buscar."
    params: dict = {"limit": 1}
    if email:
        params["email"] = email
    if cpf:
        params["cpf"] = cpf
    data = client.get("/customers", params)
    customers = data.get("Customers", [])
    if not customers:
        return "Cliente não encontrado com os dados informados."
    c = customers[0].get("Customer", customers[0])
    lines = [
        f"**Cliente encontrado**",
        f"ID: {c['id']}",
        f"Nome: {c.get('name', 'N/A')}",
        f"E-mail: {c.get('email', 'N/A')}",
        f"CPF: {c.get('cpf', 'N/A')}",
        f"Telefone: {c.get('phone', 'N/A')}",
        f"Cadastrado em: {c.get('created', 'N/A')[:10]}",
    ]
    return "\n".join(lines)


@tool
def get_customer_addresses(customer_id: int) -> str:
    """Retorna os endereços cadastrados de um cliente pelo ID.
    Use quando o cliente quiser confirmar o endereço de entrega."""
    data = client.get(f"/customers/{customer_id}/addresses")
    addresses = data.get("CustomerAddresses", [])
    if not addresses:
        return "Nenhum endereço cadastrado para este cliente."
    lines = [f"Endereços do cliente #{customer_id}:\n"]
    for item in addresses:
        a = item.get("CustomerAddress", item)
        lines.append(
            f"• {a.get('address', '')} {a.get('number', '')}, {a.get('complement', '')} — "
            f"{a.get('neighborhood', '')}, {a.get('city', '')}/{a.get('state', '')} — CEP: {a.get('zip_code', 'N/A')}"
        )
    return "\n".join(lines)
