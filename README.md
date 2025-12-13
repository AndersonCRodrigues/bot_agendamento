# 🤖 Bot Agendador Inteligente Multi-Nicho v2.1

## Sistema de agendamento conversacional com LangGraph, arquitetura otimizada para economia de tokens, personalização profunda por *tenant* e intervenção do dono em tempo real (*Owner Interaction*).

O sistema opera como uma Máquina de Estados Finitos (FSM) que converte *leads* em agendamentos confirmados através de conversação natural, respeitando regras de negócio rígidas e adaptando comportamento através de 6 dimensões configuráveis por empresa.

-----

## ✅ Visão Geral e Principais Características

### Principais Características

  * **Economia de 95-97% em tokens** através de filtragem inteligente de agenda.
  * **Arquitetura Zero-Write** - backend recebe apenas diretivas estruturadas.
  * **Personalização simplificada** - 6 dimensões de configuração essenciais.
  * **Garantias de integridade** - validação automática de dados cadastrais.
  * **Multi-nicho** - adaptável para saúde, estética, jurídico, serviços gerais.
  * **Multi-idioma** - suporte nativo para Português (BR), Inglês (US) e Espanhol (LA).
  * **Tracking completo** - métricas detalhadas por empresa, dia, semana, mês, ano.
  * **RAG (Retrieval Augmented Generation)** - knowledge base vetorial por empresa.

### 🆕 Nova Feature: Owner Interaction

Permite que o dono da empresa interrompa o bot e assuma o controle da conversa diretamente com o cliente, sem que o cliente perceba a transição.

**Como funciona?**

1.  Cliente conversa com bot normalmente.
2.  Dono decide intervir e envia mensagem via API (`POST /sessions/{session_id}/owner-interaction`).
3.  Bot pausa por **N minutos automaticamente** (duração configurável, default 10min).
4.  Cliente recebe a mensagem (achando que é do bot).
5.  Cliente responde $\to$ mensagem fica em fila (Resposta `202 Accepted`).
6.  Após o *timeout* **SEM nova mensagem do dono**:
      * Worker processa mensagens pendentes.
      * Bot volta a responder.
      * Backend recebe resposta via webhook.

-----

## 🏗️ Arquitetura Técnica

### Grafo de Estados (LangGraph)

O fluxo de processamento de cada mensagem segue a seguinte Máquina de Estados Finitos:

$$
\text{LOAD} \to \text{CHECK\_INTEGRITY} \to \text{SENTIMENT} \to \text{INTENT} \to \text{EXTRACT\_ENTITIES} \to \text{FILTER\_AVAILABILITY} \to \text{VALIDATE} \to \text{RESPOND} \to \text{PROCESS} \to \text{SAVE}
$$

#### Nós do Grafo

1.  **LOAD\_CONTEXT**: Carrega agenda completa + histórico + RAG no state.
2.  **CHECK\_INTEGRITY**: Valida completude de cadastro (nome + email).
3.  **SENTIMENT**: Análise de sentimento (8 categorias).
4.  **INTENT**: Análise de intenção (5 categorias).
5.  **EXTRACT\_ENTITIES**: Extração determinística sem LLM (regex).
6.  **FILTER\_AVAILABILITY**: Filtragem local da agenda (economia massiva).
7.  **VALIDATE**: Garante execução obrigatória das *tools*.
8.  **RESPOND**: Gera resposta usando apenas agenda filtrada + RAG.
9.  **PROCESS**: Valida e enriquece diretivas.
10. **SAVE**: Persiste sessão e métricas.

### Otimização de Tokens

| Componente | Antes (Sistema Tradicional) | Depois (Sistema Otimizado) | Economia |
| :--- | :--- | :--- | :--- |
| Agenda completa | 8000 tokens | 150 tokens (filtrada) | 98.1% |
| Extração entidades | 500 tokens | 0 tokens (regex) | 100% |
| Histórico | 2000 tokens | 200 tokens | 90% |
| Prompt base | 1500 tokens | 300 tokens | 80% |
| **TOTAL** | **\~12300 tokens/request** | **\~700 tokens/request** | **94.3%** |

### 🏗️ Arquitetura Owner Interaction

O fluxo de intervenção humana é assíncrono e confiável:

  * **Backend Principal (Seu sistema)** $\to$ Envia `POST /chat` ou `POST /owner-interaction`.
  * **Bot API (FastAPI)** $\to$ Verifica pausa $\to$ Enfileira job no Redis se pausado (`202 Accepted`).
  * **Redis Queue** $\to$ Armazena jobs com `defer_until` (timeout).
  * **Worker ARQ** $\to$ Processa o job agendado após o *timeout* $\to$ Envia resposta via Webhook (com retry).

-----

## 🔧 Instalação e Configuração

### Pré-requisitos

  * Python 3.10+
  * MongoDB Atlas (com suporte a Vector Search)
  * OpenAI API Key (GPT-4 recomendado)
  * Redis

### Setup Inicial

```bash
git clone <repository-url>
cd bot-agendamento

cp .env.example .env

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 1\. Configuração do MongoDB Atlas Vector Search Index

Este índice (`knowledge_vector_index`) é **essencial** para o RAG. Deve ser criado na *collection* `company_knowledge_base`.

```json
{
  "name": "knowledge_vector_index",
  "type": "vectorSearch",
  "definition": {
    "fields": [
      {
        "type": "vector",
        "path": "embedding",
        "numDimensions": 512,
        "similarity": "cosine"
      },
      {
        "type": "filter",
        "path": "company_id"
      },
      {
        "type": "filter",
        "path": "is_active"
      }
    ]
  }
}
```

### 2\. Variáveis de Ambiente

No arquivo `.env`:

```ini
# .env

# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net
MONGODB_DB_NAME=scheduling_bot

# OpenAI
OPENAI_API_KEY=sk-...

# Redis (para filas)
REDIS_URL=redis://localhost:6379

# Webhook do seu backend
MAIN_BACKEND_WEBHOOK_URL=https://seu-backend.com/webhook/bot-reply
WEBHOOK_SECRET_TOKEN=seu_token_super_secreto_aqui

# Ambiente
ENVIRONMENT=production
LOG_LEVEL=INFO
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o
TOOL_MODEL=gpt-4o-mini
SESSION_TTL_DAYS=30
```

### 3\. Execução

| Terminal | Comando |
| :--- | :--- |
| **Redis** | `docker run -d -p 6379:6379 redis:alpine` (ou `redis-server`) |
| **API** | `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |
| **Worker** | `arq app.worker.WorkerSettings` |

-----

## 👤 Personalização por Empresa

### 6 Dimensões Configuráveis

| Dimensão | Tipo | Valores permitidos (Exemplos) | Padrão |
| :--- | :--- | :--- | :--- |
| **1. Nicho de Mercado** (`nicho_mercado`) | String livre | "Clínica Médica", "Barbearia Premium" | *Obrigatório* |
| **2. Tom de Voz** (`tom_voz`) | Enum fixo | "Profissional", "Amigável", "Formal", "Entusiasta" | `"Profissional"` |
| **3. Idioma** (`idioma`) | Enum fixo | "pt-BR", "en-US", "es-LA" | `"pt-BR"` |
| **4. Uso de Emojis** (`uso_emojis`) | Boolean | `true`, `false` | `true` |
| **5. Frequência de CTA** (`frequencia_cta`)| Enum fixo | "minima", "normal", "maxima" | `"normal"` |
| **6. Estilo de Despedida** (`estilo_despedida`)| String livre | "Até logo\! 👋", "Cuide-se bem\!" | `"padrão"` |

### Configurações Fixas (Não Personalizáveis)

1.  **Confidencialidade:** Sempre Ativa.
2.  **Nível de Empatia:** Sempre Alto.
3.  **Extensão de Respostas:** Sempre Concisa.
4.  **Estilo de Persuasão:** Sempre Suave.
5.  **Reação a Erros:** Sempre Educada.
6.  **Tratamento:** Sempre "Você".
7.  **Gírias:** Sempre Desativadas.

-----

## 📋 Diretivas de Resposta (*Output*)

### Diretiva 1: `normal`

  * **Descrição:** Conversação em andamento, sem atualização crítica de dados.

### Diretiva 2: `update_user`

  * **Descrição:** Indica ao backend principal que o cadastro do cliente foi atualizado.
  * **Payload:** Contém `nome`, `email` e/ou `telefone`. **Apenas campos alterados são preenchidos.**

**Exemplo:**

```json
{
  "directives": {
    "type": "update_user",
    "payload_update": {
      "nome": "João Silva",
      "email": "joao@email.com",
      "telefone": null
    }
  }
}
```

### Diretiva 3: `appointment_confirmation`

  * **Descrição:** Agendamento confirmado e validado.
  * **Payload CRÍTICO:** Requer `profissional_id`, `servico_id`, `data`, `hora` (todos usando IDs da agenda, não nomes).

**Exemplo:**

```json
{
  "directives": {
    "type": "appointment_confirmation",
    "payload_update": null,
    "payload_appointment": {
      "profissional_id": "A1",
      "profissional_name": "Ana Ribeiro",
      "servico_id": "S1",
      "servico_name": "Limpeza de Pele",
      "data": "2025-12-10",
      "hora": "09:00"
    }
  }
}
```

-----

## 📡 API Reference - Endpoints Completos

### 1\. Chat & Owner Interaction

#### `POST /chat`

Endpoint principal de conversação. Inclui a agenda completa.

**Request Body (Exemplo COMPLETO com Agenda):**

```json
{
  "session_id": "5521999887766",
  "company": {
    "id": "clinica_abc",
    "nome": "Clínica ABC",
    "config_override": null,
    "agenda": {
      "professionals": {
        "A1": {
          "id": "A1",
          "name": "Ana Ribeiro",
          "services": ["S1", "S2"]
        },
        "A2": {
          "id": "A2",
          "name": "Maria Santos",
          "services": ["S1", "S3"]
        }
      },
      "services": {
        "S1": {
          "id": "S1",
          "name": "Limpeza de Pele",
          "duration": 60,
          "price": 180
        },
        "S3": {
          "id": "S3",
          "name": "Consulta Fisioterapia",
          "duration": 60,
          "price": 150
        }
      },
      "availability": {
        "A1": {
          "S1": {
            "2025-12-10": ["08:00", "09:00", "10:00", "13:00"],
            "2025-12-11": ["14:00", "15:00"]
          }
        },
        "A2": {
          "S3": {
            "2025-12-10": ["13:00", "14:00"]
          }
        }
      }
    }
  },
  "cliente": {
    "telefone": "5521999887766",
    "nome": "João Silva",
    "email": "joao@email.com",
    "mensagem": "Quero fazer limpeza de pele amanhã de manhã"
  }
}
```

**Response 202 (Accepted - Bot em Pausa):**

```json
{
  "status": "queued",
  "session_id": "5521999887766",
  "paused_until": "2025-12-12T10:40:00Z",
  "detail": "Bot em pausa. Resposta será enviada via webhook."
}
```

#### `POST /sessions/{session_id}/owner-interaction`

**Request:**

```bash
curl -X POST http://localhost:8000/sessions/5521999887766/owner-interaction \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Olá João! Aqui é o Dr. Silva...",
    "pause_minutes": 10
  }'
```

**Response 200:**

```json
{
  "status": "paused",
  "session_id": "5521999887766",
  "paused_until": "2025-12-12T10:40:00Z",
  "pause_duration_minutes": 10,
  "detail": "Bot pausado por 10 minutos."
}
```

### 2\. Companies - Configuração de Empresas

| Endpoint | Método | Descrição |
| :--- | :--- | :--- |
| `/companies/{company\_id}/config` | `POST` | Cria ou atualiza configuração comportamental. |
| `/companies/{company\_id}/config` | `GET` | Recupera configuração. **Response Exemplo:** `{"company_id": "clinica_abc", "config": {...}}` |
| `/companies` | `GET` | Lista empresas. **Response Exemplo:** `{"total": 150, "companies": [...]}` |
| `/companies/{company\_id}/config` | `DELETE` | Desativa configuração (soft delete). |

### 3\. Knowledge Base (RAG) - Sistema de FAQs

| Endpoint | Método | Descrição |
| :--- | :--- | :--- |
| `/knowledge` | `POST` | Cria nova entrada (pergunta/resposta) e gera embedding. **Response Exemplo:** `{"status": "success", "entry_id": "...", "embedding_generated": true}` |
| `/knowledge` | `GET` | Lista FAQs. **Query Params:** `company_id`, `category`, `skip`, `limit`. |
| `/knowledge/bulk` | `POST` | Criação em massa de FAQs. **Response Exemplo:** `{"status": "success", "count": 2, "ids": [...]}` |
| `/knowledge/{entry\_id}` | `PUT` | Atualiza FAQ. **Response Exemplo:** `{"status": "success", "entry_id": "...", "embedding_regenerated": true}` |
| `/knowledge/{entry\_id}` | `DELETE` | Remove FAQ. |

### 4\. Métricas - Consumo de Tokens

| Endpoint | Método | Descrição |
| :--- | :--- | :--- |
| `/metrics/usage` | `GET` | Retorna consumo de tokens por período (`daily` | `weekly`...). |
| `/metrics/ranking` | `GET` | Ranking de empresas por consumo total de tokens. |

### 5\. Sessões - Gerenciamento de Conversas

| Endpoint | Método | Descrição |
| :--- | :--- | :--- |
| `/sessions/{session\_id}` | `GET` | Obtém histórico completo da sessão (inclui `rag_context_used`, `summary`, `customer_context`). **Response 404:** `{"detail": "Sessao ... nao encontrada"}` |
| `/sessions/{session\_id}` | `DELETE` | Remove sessão (reset de conversa). |

### 6\. Sistema - Health Checks & Filas

| Endpoint | Método | Descrição |
| :--- | :--- | :--- |
| `/health` | `GET` | Status básico da API. |
| `/health/ready` | `GET` | Verifica se todos os serviços (`mongodb`, `openai`) estão funcionando. |
| `/queue/status` | `GET` | Status da fila de jobs (jobs pendentes, jobs processando). **Response Exemplo:** `{"jobs_pending": 5, "jobs_processing": 2}` |
| `/dlq/failures` | `GET` | Lista webhooks que falharam após 3 tentativas. **Query Param:** `reprocessed=false`. |

-----

## 🔒 Segurança do Webhook

Para garantir a legitimidade da origem da resposta do bot, seu backend deve validar o `WEBHOOK_SECRET_TOKEN` no cabeçalho `X-Webhook-Token`.

```python
# Exemplo em Python (FastAPI)
from fastapi import Header, HTTPException

@app.post("/webhook/bot-reply")
async def receive_bot_reply(
    payload: dict,
    x_webhook_token: str = Header(None)
):
    # 1. Valida token
    if x_webhook_token != os.getenv("WEBHOOK_SECRET_TOKEN"):
        raise HTTPException(status_code=401, detail="Invalid token")

    # 2. Processa resposta
    # ...
```

-----

## 🎯 Casos de Uso e Fluxos Detalhados

### Cenário 1: Dono Envia 1 Mensagem (Exemplo do Reset de Timer)

| Tempo | Agente | Ação / Status | Detalhe |
| :--- | :--- | :--- | :--- |
| T0 | Cliente | "Quero agendar consulta" | Bot responde normalmente. |
| T2 | Dono | **POST /owner-interaction** | Bot pausa até T12 (10 min). |
| T3 | Cliente | "Confirmo quinta às 9h" | Mensagem enfileirada $\to$ Backend recebe **202 Accepted**. |
| T12 | Worker | **Processa T3** | Bot: "Agendamento confirmado\!..." $\to$ **Webhook enviado**. |

### Cenário 2: Dono Envia Múltiplas Mensagens (*Timer Reset*)

| Tempo | Agente | Ação / Status | Detalhe |
| :--- | :--- | :--- | :--- |
| T0 | Dono | **POST /owner-interaction** | Bot pausa até T10 (Timer 10min). |
| T5 | Dono | **POST /owner-interaction** | **Timer RESETA** para T15. |
| T9 | Dono | **POST /owner-interaction** | **Timer RESETA** para T19. |
| T19 | Worker | **Acorda** | Verifica: última msg foi do OWNER. **NÃO processa** jobs pendentes. |

### Protocolos de Conversação

1.  **Barreira de Cadastro:** O sistema bloqueia agendamento até ter Nome completo e Email válido.
2.  **Protocolo de Oferta ("Ou/Ou"):** Sempre apresentar opções concretas ("Tenho quinta às 14h ou sexta às 10h. Qual prefere?") em vez de perguntas abertas.
3.  **Protocolo Anti-Cancelamento:** Na primeira solicitação de cancelamento, o bot **oferece reagendamento** antes de processar o cancelamento.

-----

## 🚨 Solução de Problemas (Troubleshooting)

| Problema | Sintoma/Causa Mais Comum | Solução Definitiva |
| :--- | :--- | :--- |
| **Tokens muito altos** | Agenda completa sendo injetada no prompt. | Verificar logs do nó `filter_availability`: o sistema deve encontrar e injetar apenas a agenda filtrada (ex: 150 tokens). |
| **RAG não funciona** | Índice `knowledge_vector_index` não existe no MongoDB Atlas. | Criar/verificar o índice de Vector Search na *collection* `company_knowledge_base`. |
| **LLM não confirma** | Falta de um dos 4 campos (`profissional_id`, `servico_id`, `data`, `hora`) OU falta da palavra de confirmação. | Bot deve retornar `type: "normal"` para solicitar a informação faltante. |
| **IDs incorretos** | LLM usa nomes ao invés de IDs na `payload_appointment`. | Reforçar no prompt: *não use nomes, use APENAS IDs*. Nó `PROCESS` valida isso. |
| **Webhook falhando** | `X-Webhook-Token` incorreto ou `MAIN_BACKEND_WEBHOOK_URL` inalcançável. | Testar `curl` e verificar logs do Worker/DLQ. |

-----

**Versão:** 2.1.0