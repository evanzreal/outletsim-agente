# OutletSIM — Agente de IA: Arquitetura e Segurança

Documento técnico para homologação com o time Partner Tech da Tray.

---

## 1. Visão Geral

O Agente de IA da OutletSIM é um assistente conversacional integrado à API da Tray, construído sobre o framework **LangGraph** (Python). Ele responde perguntas de clientes sobre produtos, preços, estoque e status de pedidos, usando a API oficial da Tray como única fonte de dados.

```
Cliente (browser)
      │  HTTP POST /chat
      ▼
┌─────────────────┐
│   FastAPI API   │  ← valida e sanitiza entrada via Pydantic
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           LangGraph Agent               │
│                                         │
│  [agent node] ──tool_calls──▶ [tools]  │
│       ▲                          │      │
│       └──────────────────────────┘      │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   Tray API      │  ← OAuth 2.0 com auto-refresh de token
└─────────────────┘
```

---

## 2. Estrutura do Projeto

```
app/
├── api.py            # Camada HTTP (FastAPI) — entrada e saída
├── agent.py          # Grafo LangGraph — lógica de decisão do agente
├── tray/
│   └── client.py     # Cliente HTTP para a API Tray (OAuth + retry)
├── tools/
│   └── tray_tools.py # 5 tools que encapsulam os endpoints da Tray
└── static/
    └── index.html    # Frontend de demonstração (chat UI)
main.py               # Entrypoint uvicorn
requirements.txt
.env.example          # Template de variáveis de ambiente (sem segredos)
```

---

## 3. Endpoints Expostos pela API

| Método | Rota       | Descrição                                      |
|--------|------------|------------------------------------------------|
| `GET`  | `/`        | Serve o frontend de demonstração (chat UI)     |
| `POST` | `/chat`    | Endpoint principal — recebe mensagem e histórico, retorna resposta do agente |
| `GET`  | `/health`  | Health check (monitoramento / uptime)          |

### Contrato do `/chat`

**Request:**
```json
{
  "message": "tem notebook disponível?",
  "history": [
    { "role": "user",      "content": "olá" },
    { "role": "assistant", "content": "Olá! Como posso ajudar?" }
  ]
}
```

**Response:**
```json
{
  "response": "Encontrei 4 notebooks disponíveis. O mais barato é..."
}
```

---

## 4. Endpoints Consumidos na API Tray

Todos os requests à Tray são feitos pelo módulo `app/tray/client.py` via HTTPS.

| Endpoint Tray                        | Tool que usa               | Finalidade                        |
|--------------------------------------|----------------------------|-----------------------------------|
| `POST /web_api/auth`                 | `client._refresh_access_token` | Renovação automática de token OAuth |
| `GET /web_api/search?query=...`      | `search_products`          | Busca livre por palavra-chave     |
| `GET /web_api/products/{id}`         | `get_product_details`      | Detalhes de um produto específico |
| `GET /web_api/categories`            | `list_categories` / `search_products_by_category` | Listagem e busca por categoria    |
| `GET /web_api/products?category_id=` | `search_products_by_category` | Produtos filtrados por categoria |
| `GET /web_api/orders/{id}`           | `get_order_status`         | Status e rastreio de pedido       |

### Parâmetros de segurança em todas as chamadas
- `available=1` nas buscas de produto — nunca expõe produtos inativos
- `limit` máximo de 50 (teto da própria API Tray)
- Timeout fixo de **15 segundos** por request
- HTTP 404 tratado silenciosamente (retorna `{}`) sem vazar stacktrace

---

## 5. Autenticação e Segurança OAuth

### Fluxo de token
```
Inicialização
    │
    ▼
Carrega TRAY_ACCESS_TOKEN do .env
    │
    ▼
A cada request à API Tray:
    ├── token válido? → usa direto
    └── token expirado? → POST /auth com refresh_token → atualiza em memória
```

- **Nenhuma credencial** (consumer_key, consumer_secret, tokens) é exposta em código ou logs
- Todas as chaves são lidas exclusivamente de variáveis de ambiente (`.env` / sistema)
- O `.env` está no `.gitignore` — nunca comitado no repositório
- O repositório público contém apenas `.env.example` com placeholders

### Credenciais em tempo de execução
```
TRAY_CONSUMER_KEY      → carregado via os.getenv()
TRAY_CONSUMER_SECRET   → carregado via os.getenv()
TRAY_ACCESS_TOKEN      → carregado via os.getenv(), atualizado em memória no refresh
TRAY_REFRESH_TOKEN     → carregado via os.getenv(), atualizado em memória no refresh
OPENROUTER_API_KEY     → carregado via os.getenv()
```

---

## 6. Guardrails do Agente

### 6.1 Escopo restrito por system prompt
O agente possui um `SYSTEM_PROMPT` que define explicitamente:
- O que pode fazer: busca de produtos, categorias, detalhes, pedidos
- O que **não pode fazer**: suporte técnico avançado, trocas, devoluções — nesses casos redireciona ao SAC
- Responde **apenas em português**

### 6.2 Dados sempre vindos da Tray — nunca inventados
O agente só responde sobre produtos após chamar uma das 5 tools. As tools são a única fonte de verdade:
- `search_products` — busca na API Tray
- `get_product_details` — detalhe real do produto
- `list_categories` — categorias ativas com produto
- `search_products_by_category` — produtos reais por categoria
- `get_order_status` — status real do pedido

O LLM não tem permissão de "imaginar" produtos, preços ou estoques — qualquer afirmação de produto precisa passar por uma tool call antes.

### 6.3 Validação de entrada (Pydantic)
Todo payload recebido no `/chat` é validado antes de chegar ao agente:

```python
class Message(BaseModel):
    role: str      # aceita: "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []
```

Payloads malformados retornam `422 Unprocessable Entity` antes de tocar qualquer lógica.

### 6.4 Histórico limitado no frontend
O frontend mantém no máximo **10 turnos** (20 mensagens) no histórico enviado ao backend — evita janelas de contexto excessivas e abuso por mensagens muito longas.

### 6.5 Tratamento de erros sem vazamento
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```
Erros internos retornam HTTP 500 com mensagem genérica — stacktraces nunca chegam ao cliente.

---

## 7. Conformidade com os Limites da API Tray

| Regra Tray                         | Como o agente respeita              |
|------------------------------------|-------------------------------------|
| 180 req/min por loja               | Cada conversa faz no máximo 2–3 chamadas por turno (tool calls sequenciais) |
| 10.000 req/dia por loja            | Uso conversacional típico: ~5 req/conversa; suporta ~2.000 conversas/dia dentro do limite |
| `available=1` obrigatório em buscas | Aplicado em todos os endpoints de produto |
| Token com expiração                | Auto-refresh transparente antes de cada chamada expirada |

---

## 8. Stack de Tecnologia

| Componente         | Tecnologia              | Versão mínima |
|--------------------|-------------------------|---------------|
| Linguagem          | Python                  | 3.12          |
| Framework de agente | LangGraph + LangChain  | 0.2 / 0.3     |
| Modelo de linguagem | GPT-4o-mini via OpenRouter | —          |
| API HTTP           | FastAPI + Uvicorn       | 0.115         |
| Cliente HTTP       | httpx                   | 0.27          |
| Validação          | Pydantic v2             | 2.9           |

---

## 9. Como Executar (Ambiente de Teste)

```bash
# 1. Instalar dependências
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# editar .env com as credenciais fornecidas pela Tray

# 3. Iniciar o servidor
.venv/bin/python main.py
# → http://localhost:8000
```

---

## 10. O que NÃO está no escopo desta versão (v1)

Os itens abaixo são melhorias previstas para versões futuras e **não são necessários para homologação**:

- Persistência de sessão em banco de dados (Redis/PostgreSQL)
- Rate limiting no próprio servidor (atualmente delegado à infraestrutura)
- Autenticação de usuário no endpoint `/chat`
- Integração com WhatsApp / outros canais
- Webhook para eventos da Tray (ex: atualização de estoque)
