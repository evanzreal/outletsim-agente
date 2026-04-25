# Documentação de Endpoints — Agente de IA OutletSIM
### Integração com a API Tray | Homologação Partner Tech

---

## Informações Gerais

**Aplicação:** Agente de IA OutletSIM  
**Base URL:** `https://{store_id}.commercesuite.com.br/web_api`  
**Autenticação:** OAuth 2.0 — `access_token` enviado como query parameter em todos os endpoints  
**Timeout por request:** 15 segundos  
**Rate limit respeitado:** máximo ~3 chamadas por turno de conversa (bem abaixo do limite de 180 req/min)

---

## 1. Autenticação — Geração de Token

**Endpoint:** `POST /web_api/auth`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/auth`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "consumer_key": "{CONSUMER_KEY}",
  "consumer_secret": "{CONSUMER_SECRET}",
  "code": "{AUTHORIZATION_CODE}"
}
```

**Finalidade:** Geração inicial do `access_token` e `refresh_token` após instalação do app pelo lojista.

**Resposta esperada:**
```json
{
  "access_token": "APP_ID-XXXX-STORE_ID-XXXXXX-...",
  "refresh_token": "...",
  "date_expiration_access_token": "2026-04-22 17:24:33",
  "date_expiration_refresh_token": "2026-05-22 14:24:33"
}
```

---

## 2. Renovação de Token

**Endpoint:** `POST /web_api/auth`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/auth`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "consumer_key": "{CONSUMER_KEY}",
  "consumer_secret": "{CONSUMER_SECRET}",
  "refresh_token": "{REFRESH_TOKEN}"
}
```

**Finalidade:** Renovação automática do `access_token` quando expirado, sem necessidade de reautorização pelo lojista. A aplicação verifica a validade do token a cada chamada e executa o refresh de forma transparente.

---

## 3. Busca de Produtos por Palavra-chave

**Endpoint:** `GET /web_api/search`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/search?access_token={TOKEN}&query={TERMO}&limit=10&available=1`

**Headers:** *(nenhum adicional — autenticação via query param)*

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `access_token` | string | Token de autenticação |
| `query` | string | Termo de busca livre |
| `limit` | int | Quantidade de resultados (padrão: 10, máx: 50) |
| `available` | int | `1` = apenas produtos disponíveis |

**Finalidade:** Busca livre de produtos por nome ou palavra-chave. Acionada quando o cliente do chat pergunta por um produto específico (ex: "tem notebook?", "quero uma impressora").

**Exemplo de chamada:**
```
GET /web_api/search?access_token=TOKEN&query=notebook&limit=10&available=1
```

---

## 4. Detalhes de Produto

**Endpoint:** `GET /web_api/products/{id}`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/products/{product_id}?access_token={TOKEN}`

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `access_token` | string | Token de autenticação |
| `product_id` | int | ID do produto (path param) |

**Finalidade:** Retorna dados completos de um produto: descrição, preço, estoque, marca, modelo, garantia, peso e variações. Acionada quando o cliente solicita detalhes de um produto específico após vê-lo na listagem.

**Exemplo de chamada:**
```
GET /web_api/products/1407711783?access_token=TOKEN
```

---

## 5. Listagem de Categorias

**Endpoint:** `GET /web_api/categories`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/categories?access_token={TOKEN}&limit=100&active=1&has_product=1`

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `access_token` | string | Token de autenticação |
| `limit` | int | Máximo de categorias retornadas |
| `active` | int | `1` = apenas categorias ativas |
| `has_product` | int | `1` = apenas categorias com produtos |

**Finalidade:** Lista as categorias disponíveis para o cliente navegar. Filtra automaticamente categorias inativas ou sem produto.

---

## 6. Produtos por Categoria

**Endpoint:** `GET /web_api/products`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/products?access_token={TOKEN}&category_id={ID}&available=1&limit=10&order=price`

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `access_token` | string | Token de autenticação |
| `category_id` | int | ID da categoria |
| `available` | int | `1` = apenas disponíveis |
| `limit` | int | Quantidade de resultados |
| `order` | string | Campo de ordenação (`price`) |

**Finalidade:** Busca produtos de uma categoria específica. A aplicação resolve o nome da categoria para o ID internamente antes de chamar este endpoint.

**Exemplo de chamada:**
```
GET /web_api/products?access_token=TOKEN&category_id=703583&available=1&limit=10&order=price
```

---

## 7. Produtos Mais Vendidos

**Endpoint:** `GET /web_api/products`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/products?access_token={TOKEN}&available=1&limit=10&order=quantity_sold&sort=desc`

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `access_token` | string | Token de autenticação |
| `available` | int | `1` = apenas disponíveis |
| `order` | string | `quantity_sold` = ordenar por quantidade vendida |
| `sort` | string | `desc` = mais vendidos primeiro |

**Finalidade:** Lista os produtos mais populares da loja. Acionada quando o cliente pede recomendações ou produtos mais vendidos.

---

## 8. Listagem de Marcas

**Endpoint:** `GET /web_api/brands`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/brands?access_token={TOKEN}&limit=100`

**Finalidade:** Lista todas as marcas disponíveis na loja. Usada para apresentar as marcas ao cliente ou como passo anterior à busca por marca.

---

## 9. Produtos por Marca

**Endpoint:** `GET /web_api/products`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/products?access_token={TOKEN}&brand_id={ID}&available=1&limit=10&order=price`

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `brand_id` | int | ID da marca (resolvido internamente a partir do nome) |
| `available` | int | `1` = apenas disponíveis |

**Finalidade:** Busca produtos filtrados por marca. Acionada quando o cliente pergunta por produtos de uma marca específica (ex: "tem produto da Samsung?").

---

## 10. Status de Pedido

**Endpoint:** `GET /web_api/orders/{id}`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/orders/{order_id}?access_token={TOKEN}`

**Finalidade:** Retorna o status atual de um pedido (aguardando pagamento, em separação, enviado, entregue, etc.), transportadora e código de rastreio. Acionada quando o cliente informa o número do pedido.

**Exemplo de chamada:**
```
GET /web_api/orders/12345?access_token=TOKEN
```

---

## 11. Pedido Completo (com Itens e NF)

**Endpoint:** `GET /web_api/orders/{id}/complete`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/orders/{order_id}/complete?access_token={TOKEN}`

**Finalidade:** Retorna o pedido com todos os dados: itens comprados, quantidades, valores, nota fiscal (chave e CNPJ) e código de rastreio. Acionada quando o cliente solicita detalhes completos ou a nota fiscal.

---

## 12. Histórico de Pedidos do Cliente

**Endpoint:** `GET /web_api/orders`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/orders?access_token={TOKEN}&customer_id={ID}&limit=5&order=date&sort=desc`

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `customer_id` | int | ID do cliente |
| `limit` | int | Quantidade de pedidos retornados |
| `order` | string | `date` = ordenar por data |
| `sort` | string | `desc` = mais recentes primeiro |

**Finalidade:** Lista o histórico de pedidos de um cliente. Acionada após identificar o cliente via e-mail ou CPF.

---

## 13. Busca de Cliente

**Endpoint:** `GET /web_api/customers`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/customers?access_token={TOKEN}&email={EMAIL}` ou `&cpf={CPF}`

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `email` | string | E-mail do cliente (opcional) |
| `cpf` | string | CPF do cliente (opcional) |
| `limit` | int | `1` (busca por identificador único) |

**Finalidade:** Identifica o cliente pelo e-mail ou CPF para obter o ID e realizar consultas subsequentes (pedidos, endereços).

---

## 14. Endereços do Cliente

**Endpoint:** `GET /web_api/customers/{id}/addresses`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/customers/{customer_id}/addresses?access_token={TOKEN}`

**Finalidade:** Retorna os endereços de entrega cadastrados para o cliente. Acionada quando o cliente quer confirmar o endereço de um pedido.

---

## 15. Cálculo de Frete

**Endpoint:** `GET /web_api/freight/calculate`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/freight/calculate?access_token={TOKEN}&zip_code={CEP}&products[0][product_id]={ID}&products[0][quantity]={QTD}`

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `zip_code` | string | CEP de destino (somente números) |
| `products[0][product_id]` | int | ID do produto |
| `products[0][quantity]` | int | Quantidade |

**Finalidade:** Calcula o frete e prazo de entrega para um produto até o CEP informado pelo cliente. Retorna todas as opções de transportadora disponíveis com valor e prazo.

**Exemplo de chamada:**
```
GET /web_api/freight/calculate?access_token=TOKEN&zip_code=01310100&products[0][product_id]=261&products[0][quantity]=1
```

---

## 16. Métodos de Frete Disponíveis

**Endpoint:** `GET /web_api/freight/methods`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/freight/methods?access_token={TOKEN}&limit=20`

**Finalidade:** Lista as transportadoras e modalidades de envio configuradas na loja. Usada para informar ao cliente as opções gerais de entrega disponíveis.

---

## 17. Cupons de Desconto

**Endpoint:** `GET /web_api/coupons`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/coupons?access_token={TOKEN}&limit=20&active=1`

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `active` | int | `1` = apenas cupons ativos |

**Finalidade:** Lista os cupons de desconto ativos na loja. Acionada quando o cliente pergunta sobre promoções ou descontos disponíveis.

---

## 18. Detalhes de Cupom

**Endpoint:** `GET /web_api/coupons`  
**URL completa:** `https://{store_id}.commercesuite.com.br/web_api/coupons?access_token={TOKEN}&code={CODIGO_CUPOM}&limit=1`

**Parâmetros:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `code` | string | Código do cupom informado pelo cliente |

**Finalidade:** Valida e retorna os detalhes de um cupom específico: desconto (percentual ou valor fixo), validade, pedido mínimo e limite de uso por cliente. Acionada quando o cliente informa um código de cupom.

---

## Padrão de Autenticação em Todas as Chamadas

Todos os endpoints acima utilizam o `access_token` como query parameter:

```
GET https://{store_id}.commercesuite.com.br/web_api/{recurso}?access_token={TOKEN}
```

A aplicação gerencia o ciclo de vida do token automaticamente:
1. Ao iniciar, carrega o `access_token` e sua data de expiração das variáveis de ambiente
2. Antes de cada chamada, verifica se o token está válido
3. Se expirado, executa automaticamente o refresh via `POST /web_api/auth` com o `refresh_token`
4. Atualiza o token em memória sem interrupção do serviço

---

## Conformidade com Limites da API Tray

| Regra | Como a aplicação respeita |
|---|---|
| 180 req/min | Cada turno de conversa executa no máximo 2–3 tool calls sequenciais |
| 10.000 req/dia | Uso conversacional típico: ~5 req/conversa |
| `available=1` | Aplicado em todas as buscas de produto |
| Token com expiração | Auto-refresh transparente antes de qualquer chamada expirada |
