# Bot Agendador Inteligente Multi-Nicho v2.1

Sistema de agendamento conversacional baseado em LangGraph com arquitetura otimizada para economia de tokens, personalização profunda por tenant e garantias de integridade de dados.

## Visão Geral

O sistema opera como uma Máquina de Estados Finitos (FSM) que converte leads em agendamentos confirmados através de conversação natural, respeitando regras de negócio rígidas e adaptando comportamento através de 15 dimensões configuráveis por empresa.

### Principais Características

- **Economia de 95-97% em tokens** através de filtragem inteligente de agenda
- **Arquitetura Zero-Write** - backend recebe apenas diretivas estruturadas
- **Personalização profunda** - 15 dimensões de configuração por tenant
- **Garantias de integridade** - validação automática de dados cadastrais
- **Multi-nicho** - adaptável para saúde, estética, jurídico, serviços gerais
- **Tracking completo** - métricas detalhadas por empresa, dia, semana, mês, ano
- **RAG (Retrieval Augmented Generation)** - knowledge base vetorial por empresa

---

## Arquitetura Técnica

### Grafo de Estados (LangGraph)

```
LOAD → CHECK_INTEGRITY → SENTIMENT → INTENT → EXTRACT_ENTITIES →
FILTER_AVAILABILITY → VALIDATE → RESPOND → PROCESS → SAVE
```

#### Nós do Grafo

1. **LOAD_CONTEXT**: Carrega agenda completa + histórico + RAG no state (não enviado ao LLM)
2. **CHECK_INTEGRITY**: Valida completude de cadastro (nome + email)
3. **SENTIMENT**: Análise de sentimento (8 categorias)
4. **INTENT**: Análise de intenção (5 categorias)
5. **EXTRACT_ENTITIES**: Extração determinística sem LLM (regex)
6. **FILTER_AVAILABILITY**: Filtragem local da agenda (economia massiva)
7. **VALIDATE**: Garante execução obrigatória das tools
8. **RESPOND**: Gera resposta usando apenas agenda filtrada + RAG
9. **PROCESS**: Valida e enriquece diretivas
10. **SAVE**: Persiste sessão e métricas

### Otimização de Tokens

#### Antes (Sistema Tradicional)
```
Agenda completa: 8000 tokens
Contexto: 300 tokens
Histórico: 2000 tokens
Prompt base: 1500 tokens
Extração: 500 tokens
TOTAL: ~12300 tokens/request
```

#### Depois (Sistema Otimizado)
```
Agenda filtrada: 150 tokens
Contexto: 50 tokens
Histórico: 200 tokens
Prompt base: 300 tokens
Extração: 0 tokens (regex)
RAG: 200 tokens (só quando relevante)
TOTAL: ~700 tokens/request
```

**Redução: 94.3%**

---

## Instalação

### Pré-requisitos

- Python 3.10+
- MongoDB Atlas (com suporte a Vector Search)
- OpenAI API Key (GPT-4 recomendado)

### Setup Inicial

```bash
git clone <repository-url>
cd bot-agendamento

cp .env.example .env
# Edite .env com suas credenciais

python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### Configuração do MongoDB Atlas

#### 1. Criar Cluster e Database

1. Acesse [MongoDB Atlas](https://cloud.mongodb.com)
2. Crie um cluster (Free tier funciona)
3. Em "Database Access", crie um usuário
4. Em "Network Access", adicione seu IP
5. Copie a Connection String

#### 2. Configurar MongoDB Atlas Vector Search Index

**IMPORTANTE**: Este índice é essencial para o RAG funcionar.

No MongoDB Atlas UI:
1. Vá em `Database` → Seu Cluster → `Search`
2. Clique em `Create Search Index`
3. Escolha `JSON Editor`
4. Cole a seguinte configuração:

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

5. Selecione a database: `scheduling_bot`
6. Selecione a collection: `company_knowledge_base`
7. Clique em `Create Search Index`

**Nota**: O índice pode levar alguns minutos para ser construído.

#### 3. Configurar .env

```bash
MONGODB_URI=mongodb+srv://usuario:senha@cluster.mongodb.net
MONGODB_DB_NAME=scheduling_bot

OPENAI_API_KEY=sk-...

ENVIRONMENT=production
LOG_LEVEL=INFO

EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o
TOOL_MODEL=gpt-4o-mini

SESSION_TTL_DAYS=30
```

### Execução

```bash
./run.sh
```

ou

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API estará disponível em: `http://localhost:8000`

Documentação interativa: `http://localhost:8000/docs`

---

## 📡 API Reference - Endpoints Completos

### **1. Chat - Conversação Principal**

#### `POST /chat`

Endpoint principal de conversação com o bot de agendamento.

**Request Body:**

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
        "S2": {
          "id": "S2",
          "name": "Peeling Facial",
          "duration": 60,
          "price": 220
        }
      },
      "availability": {
        "A1": {
          "S1": {
            "2025-12-10": ["08:00", "09:00", "10:00"],
            "2025-12-11": ["13:00", "14:00", "15:00"]
          },
          "S2": {
            "2025-12-10": ["11:00", "12:00"]
          }
        },
        "A2": {
          "S1": {
            "2025-12-10": ["08:00", "09:00", "10:00", "11:00"]
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

**Response - Sucesso (200):**

```json
{
  "cliente_id": "5521999887766",
  "company_id": "clinica_abc",
  "response_text": "Agendamento confirmado! Limpeza de Pele com Ana Ribeiro no dia 10/12/2025 às 09h.",
  "kanban_status": "Agendado",
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
  },
  "cost_info": {
    "total_tokens": 512,
    "input_tokens": 435,
    "output_tokens": 77
  },
  "metadata": {
    "intent": "SCHEDULING",
    "sentiment": "positivo",
    "tokens": 512
  }
}
```

**Tipos de Diretivas:**

| Tipo | Quando Usar | Campos Obrigatórios |
|------|-------------|---------------------|
| `normal` | Conversação em andamento | - |
| `update_user` | Cliente forneceu dados cadastrais | `payload_update` |
| `appointment_confirmation` | Cliente confirmou agendamento | `payload_appointment` com todos os 4 campos |

---

### 📋 Exemplos Detalhados por Tipo de Diretiva

#### **Diretiva 1: `normal` - Conversação em Andamento**

**Quando usar:**
- Cliente fazendo perguntas
- Negociação de horários
- Dúvidas sobre serviços
- Primeira interação sem cadastro
- Cancelamento solicitado
- Handoff para humano

**Exemplo 1: Cliente pergunta sobre preço**

```json
{
  "cliente": {
    "telefone": "5521999887766",
    "mensagem": "Quanto custa a limpeza de pele?"
  }
}
```

**Response:**
```json
{
  "cliente_id": "5521999887766",
  "company_id": "clinica_abc",
  "response_text": "A Limpeza de Pele custa R$ 180,00 e tem duração de 60 minutos. Quer agendar?",
  "kanban_status": "Dúvida/Info",
  "directives": {
    "type": "normal",
    "payload_update": null,
    "payload_appointment": null
  },
  "metadata": {
    "intent": "INFO",
    "sentiment": "neutro"
  }
}
```

**Exemplo 2: Cliente quer cancelar (primeira menção)**

```json
{
  "cliente": {
    "telefone": "5521999887766",
    "nome": "João Silva",
    "email": "joao@email.com",
    "mensagem": "Quero cancelar meu agendamento"
  }
}
```

**Response:**
```json
{
  "response_text": "Entendo. Que tal reagendar? Tenho disponível terça às 14h ou quinta às 10h.",
  "kanban_status": "Em Atendimento",
  "directives": {
    "type": "normal",
    "payload_update": null,
    "payload_appointment": null
  },
  "metadata": {
    "intent": "CANCELLATION",
    "sentiment": "neutro"
  }
}
```

**Exemplo 3: Cliente pede atendimento humano**

```json
{
  "cliente": {
    "mensagem": "Quero falar com um atendente"
  }
}
```

**Response:**
```json
{
  "response_text": "Claro! Vou encaminhar você para atendimento humano. Aguarde um momento.",
  "kanban_status": "Handoff Humano",
  "directives": {
    "type": "normal",
    "payload_update": null,
    "payload_appointment": null
  },
  "metadata": {
    "intent": "HUMAN_HANDOFF",
    "sentiment": "neutro"
  }
}
```

---

#### **Diretiva 2: `update_user` - Atualização de Cadastro**

**Quando usar:**
- Cliente fornece nome completo (mínimo 2 palavras)
- Cliente fornece email válido (com @)
- Cliente corrige telefone
- Cliente atualiza qualquer dado pessoal

**⚠️ IMPORTANTE:** Preencha apenas os campos que o cliente mencionou. Deixe os outros como `null`.

**Exemplo 1: Cliente fornece apenas nome**

```json
{
  "cliente": {
    "telefone": "5521999887766",
    "mensagem": "Meu nome é João Silva"
  }
}
```

**Response:**
```json
{
  "response_text": "Obrigado João! Agora preciso do seu email para confirmar o cadastro.",
  "kanban_status": "Em Atendimento",
  "directives": {
    "type": "update_user",
    "payload_update": {
      "nome": "João Silva",
      "email": null,
      "telefone": null
    },
    "payload_appointment": null
  },
  "metadata": {
    "intent": "INFO",
    "sentiment": "positivo"
  }
}
```

**Exemplo 2: Cliente fornece apenas email**

```json
{
  "cliente": {
    "telefone": "5521999887766",
    "nome": null,
    "mensagem": "joao.silva@email.com"
  }
}
```

**Response:**
```json
{
  "response_text": "Email registrado! Preciso também do seu nome completo para finalizar o cadastro.",
  "kanban_status": "Em Atendimento",
  "directives": {
    "type": "update_user",
    "payload_update": {
      "nome": null,
      "email": "joao.silva@email.com",
      "telefone": null
    },
    "payload_appointment": null
  },
  "metadata": {
    "intent": "INFO",
    "sentiment": "neutro"
  }
}
```

**Exemplo 3: Cliente fornece nome E email na mesma mensagem**

```json
{
  "cliente": {
    "telefone": "5521999887766",
    "mensagem": "João Silva, joao@email.com"
  }
}
```

**Response:**
```json
{
  "response_text": "Perfeito João! Cadastro completo. Qual serviço você deseja agendar?",
  "kanban_status": "Em Atendimento",
  "directives": {
    "type": "update_user",
    "payload_update": {
      "nome": "João Silva",
      "email": "joao@email.com",
      "telefone": null
    },
    "payload_appointment": null
  },
  "metadata": {
    "intent": "INFO",
    "sentiment": "positivo"
  }
}
```

**Exemplo 4: Cliente corrige telefone**

```json
{
  "cliente": {
    "telefone": "5521999887766",
    "nome": "João Silva",
    "email": "joao@email.com",
    "mensagem": "Meu telefone correto é 5521988776655"
  }
}
```

**Response:**
```json
{
  "response_text": "Telefone atualizado para 5521988776655. Posso te ajudar com mais alguma coisa?",
  "kanban_status": "Em Atendimento",
  "directives": {
    "type": "update_user",
    "payload_update": {
      "nome": null,
      "email": null,
      "telefone": "5521988776655"
    },
    "payload_appointment": null
  },
  "metadata": {
    "intent": "INFO",
    "sentiment": "neutro"
  }
}
```

---

#### **Diretiva 3: `appointment_confirmation` - Agendamento Confirmado**

**Quando usar:**
- Cliente confirmou TODOS os 4 elementos: profissional, serviço, data e hora
- Cliente usou palavras de confirmação: "confirmo", "pode ser", "fechado", "topo", "marque"
- Cliente repetiu data + hora + profissional explicitamente

**⚠️ CRÍTICO:** Todos os 4 campos são obrigatórios:
- `profissional_id` (ex: "A1", "A2")
- `servico_id` (ex: "S1", "S2")
- `data` (formato: YYYY-MM-DD)
- `hora` (formato: HH:MM)

Se faltar qualquer um desses campos, use `type: "normal"` ao invés de `appointment_confirmation`.

**Exemplo 1: Cliente confirma opção oferecida**

```json
{
  "cliente": {
    "telefone": "5521999887766",
    "nome": "João Silva",
    "email": "joao@email.com",
    "mensagem": "Confirmo quinta às 9h com a Ana"
  }
}
```

**Response:**
```json
{
  "response_text": "Agendado! Limpeza de Pele com Ana Ribeiro, quinta-feira 10/12/2025 às 9h. Duração: 60min. Valor: R$ 180,00. Até lá!",
  "kanban_status": "Agendado",
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
  },
  "cost_info": {
    "total_tokens": 512,
    "input_tokens": 435,
    "output_tokens": 77
  },
  "metadata": {
    "intent": "SCHEDULING",
    "sentiment": "positivo"
  }
}
```

**Exemplo 2: Cliente usa palavra-chave "pode ser"**

```json
{
  "cliente": {
    "nome": "Maria Santos",
    "email": "maria@email.com",
    "mensagem": "Pode ser sexta às 14h"
  }
}
```

**Response:**
```json
{
  "response_text": "Confirmado! Peeling Facial com Maria Santos, sexta-feira 11/12/2025 às 14h. Duração: 60min. Valor: R$ 220,00.",
  "kanban_status": "Agendado",
  "directives": {
    "type": "appointment_confirmation",
    "payload_update": null,
    "payload_appointment": {
      "profissional_id": "A2",
      "profissional_name": "Maria Santos",
      "servico_id": "S2",
      "servico_name": "Peeling Facial",
      "data": "2025-12-11",
      "hora": "14:00"
    }
  },
  "metadata": {
    "intent": "SCHEDULING",
    "sentiment": "positivo"
  }
}
```

**Exemplo 3: Cliente especifica tudo de uma vez**

```json
{
  "cliente": {
    "nome": "Pedro Oliveira",
    "email": "pedro@email.com",
    "mensagem": "Quero agendar limpeza de pele com a Ana no dia 10/12 às 10h"
  }
}
```

**Response:**
```json
{
  "response_text": "Agendamento confirmado Pedro! Limpeza de Pele com Ana Ribeiro no dia 10/12/2025 às 10h. Te esperamos lá!",
  "kanban_status": "Agendado",
  "directives": {
    "type": "appointment_confirmation",
    "payload_update": null,
    "payload_appointment": {
      "profissional_id": "A1",
      "profissional_name": "Ana Ribeiro",
      "servico_id": "S1",
      "servico_name": "Limpeza de Pele",
      "data": "2025-12-10",
      "hora": "10:00"
    }
  },
  "metadata": {
    "intent": "SCHEDULING",
    "sentiment": "positivo"
  }
}
```

**Exemplo 4: Cliente usa gíria "topo"**

```json
{
  "cliente": {
    "mensagem": "Topo! Fecha aí"
  }
}
```

**Response:**
```json
{
  "response_text": "Fechado! Consulta Fisioterapia com Maria Santos, quinta-feira 10/12/2025 às 13h. Duração: 60min. Valor: R$ 150,00.",
  "kanban_status": "Agendado",
  "directives": {
    "type": "appointment_confirmation",
    "payload_update": null,
    "payload_appointment": {
      "profissional_id": "A2",
      "profissional_name": "Maria Santos",
      "servico_id": "S3",
      "servico_name": "Consulta Fisioterapia",
      "data": "2025-12-10",
      "hora": "13:00"
    }
  },
  "metadata": {
    "intent": "SCHEDULING",
    "sentiment": "positivo"
  }
}
```

---

### ❌ Exemplos de Casos INVÁLIDOS para `appointment_confirmation`

**Caso 1: Falta especificar o horário**

```json
{
  "cliente": {
    "mensagem": "Quero com a Ana na quinta"
  }
}
```

**Response (correto = type: "normal"):**
```json
{
  "response_text": "Para agendar com Ana na quinta, tenho 9h, 10h ou 13h disponíveis. Qual horário prefere?",
  "directives": {
    "type": "normal"
  }
}
```

**Caso 2: Falta confirmar explicitamente**

```json
{
  "cliente": {
    "mensagem": "E quinta de manhã tem?"
  }
}
```

**Response (correto = type: "normal"):**
```json
{
  "response_text": "Sim! Quinta de manhã tenho Ana às 9h e às 10h. Confirma qual?",
  "directives": {
    "type": "normal"
  }
}
```

**Caso 3: Cliente está só perguntando**

```json
{
  "cliente": {
    "mensagem": "Quais horários tem com a Ana?"
  }
}
```

**Response (correto = type: "normal"):**
```json
{
  "response_text": "Com Ana tenho: quinta às 9h, 10h ou sexta às 14h. Qual prefere?",
  "directives": {
    "type": "normal"
  }
}
```

---

### 🔄 Fluxo Completo: Do Primeiro Contato ao Agendamento

**Interação 1: Primeiro contato**
```
Cliente: "Oi"
Bot: "Olá! Bem-vindo à Clínica ABC. Para agendar, preciso do seu nome completo e email."
Diretiva: type="normal"
```

**Interação 2: Cliente dá nome**
```
Cliente: "João Silva"
Bot: "Obrigado João! Agora preciso do seu email."
Diretiva: type="update_user", payload_update={"nome": "João Silva"}
```

**Interação 3: Cliente dá email**
```
Cliente: "joao@email.com"
Bot: "Perfeito! Qual serviço você deseja?"
Diretiva: type="update_user", payload_update={"email": "joao@email.com"}
```

**Interação 4: Cliente escolhe serviço**
```
Cliente: "Limpeza de pele"
Bot: "Para Limpeza de Pele tenho: Ana quinta às 9h ou Maria sexta às 10h. Qual prefere?"
Diretiva: type="normal"
```

**Interação 5: Cliente confirma**
```
Cliente: "Confirmo quinta às 9h"
Bot: "Agendado! Limpeza de Pele com Ana, quinta 10/12 às 9h. Até lá!"
Diretiva: type="appointment_confirmation", payload_appointment={...todos os 4 campos}
```

**Status Codes:**

- `200` - Sucesso
- `400` - Dados inválidos
- `422` - Schema inválido
- `500` - Erro interno
- `503` - Serviço OpenAI indisponível

---

### **2. Companies - Configuração de Empresas**

#### `POST /companies/{company_id}/config`

Cria ou atualiza configuração comportamental de uma empresa.

**Path Parameters:**
- `company_id` (string) - ID único da empresa

**Request Body:**

```json
{
  "nicho_mercado": "Clínica Médica",
  "nome_bot": "Dr. Agenda",
  "tom_voz": "Empático",
  "nivel_empatia": "Alto",
  "uso_emojis": "moderado",
  "extensao_respostas": "concisa",
  "estilo_tratamento": "Você",
  "permitir_girias": false,
  "enfase_confidencialidade": true,
  "vocabularios_especificos": {
    "cliente": "paciente"
  },
  "foco_conversa": "Agendamento Direto",
  "estilo_persuasao": "suave",
  "reacao_erros": "educada",
  "frequencia_reforco_positivo": "baixa",
  "frequencia_cta": "normal",
  "estilo_despedida": "padrão"
}
```

**Response (200):**

```json
{
  "status": "success",
  "company_id": "clinica_abc",
  "updated_at": "2025-12-11T10:30:00Z"
}
```

---

#### `GET /companies/{company_id}/config`

Recupera configuração de uma empresa.

**Response (200):**

```json
{
  "company_id": "clinica_abc",
  "config": {
    "nicho_mercado": "Clínica Médica",
    "nome_bot": "Dr. Agenda",
    "tom_voz": "Empático",
    // ... demais campos
  }
}
```

---

#### `GET /companies`

Lista todas as empresas configuradas (paginado).

**Query Parameters:**
- `skip` (int) - Offset para paginação (default: 0)
- `limit` (int) - Limite de resultados (default: 50)

**Response (200):**

```json
{
  "total": 150,
  "companies": [
    {
      "company_id": "clinica_abc",
      "nome_bot": "Dr. Agenda",
      "nicho_mercado": "Clínica Médica",
      "created_at": "2025-11-15T08:00:00Z",
      "updated_at": "2025-12-01T14:30:00Z"
    }
  ]
}
```

---

#### `DELETE /companies/{company_id}/config`

Desativa configuração (soft delete).

**Response (200):**

```json
{
  "status": "success",
  "company_id": "clinica_abc"
}
```

**Response (404):**

```json
{
  "detail": "Empresa nao encontrada"
}
```

---

### **3. Knowledge Base (RAG) - Sistema de FAQs**

#### `POST /knowledge`

Cria nova entrada no knowledge base.

**Request Body:**

```json
{
  "company_id": "clinica_abc",
  "question": "Como funciona o pagamento?",
  "answer": "Aceitamos cartão, PIX e dinheiro. O pagamento é feito na recepção após o atendimento.",
  "category": "pagamento",
  "priority": 3
}
```

**Response (200):**

```json
{
  "status": "success",
  "entry_id": "674a5c8e9f1234567890abcd",
  "embedding_generated": true
}
```

---

#### `GET /knowledge`

Lista FAQs da empresa (paginado).

**Query Parameters:**
- `company_id` (string) - ID da empresa
- `category` (string, opcional) - Filtrar por categoria
- `skip` (int) - Offset (default: 0)
- `limit` (int) - Limite (default: 50)

**Response (200):**

```json
{
  "total": 25,
  "entries": [
    {
      "id": "674a5c8e9f1234567890abcd",
      "question": "Como funciona o pagamento?",
      "answer": "Aceitamos cartão, PIX e dinheiro...",
      "category": "pagamento",
      "priority": 3,
      "created_at": "2025-11-20T10:00:00Z",
      "updated_at": "2025-11-20T10:00:00Z"
    }
  ]
}
```

---

#### `PUT /knowledge/{entry_id}`

Atualiza FAQ existente.

**Request Body:**

```json
{
  "company_id": "clinica_abc",
  "question": "Como funciona o pagamento atualizado?",
  "answer": "Aceitamos cartão, PIX, dinheiro e boleto.",
  "category": "pagamento",
  "priority": 4
}
```

**Response (200):**

```json
{
  "status": "success",
  "entry_id": "674a5c8e9f1234567890abcd",
  "embedding_regenerated": true
}
```

---

#### `DELETE /knowledge/{entry_id}`

Remove FAQ (soft delete).

**Query Parameters:**
- `company_id` (string) - ID da empresa

**Response (200):**

```json
{
  "status": "success",
  "entry_id": "674a5c8e9f1234567890abcd"
}
```

---

#### `POST /knowledge/bulk`

Criação em massa de FAQs.

**Request Body:**

```json
{
  "company_id": "clinica_abc",
  "entries": [
    {
      "question": "Qual o horário de funcionamento?",
      "answer": "Segunda a sexta, 8h às 18h.",
      "category": "informacao",
      "priority": 2
    },
    {
      "question": "Aceita convênio?",
      "answer": "Sim, aceitamos Unimed e SulAmérica.",
      "category": "convenio",
      "priority": 1
    }
  ]
}
```

**Response (200):**

```json
{
  "status": "success",
  "count": 2,
  "ids": [
    "674a5c8e9f1234567890abcd",
    "674a5c8e9f1234567890abce"
  ]
}
```

---

### **4. Métricas - Consumo de Tokens**

#### `GET /metrics/usage`

Retorna consumo de tokens com múltiplas granularidades.

**Query Parameters:**
- `company_id` (string, opcional) - ID da empresa (null = todas)
- `period` (string) - `daily` | `weekly` | `monthly` | `yearly` | `total`
- `start_date` (string, opcional) - Data inicial YYYY-MM-DD
- `end_date` (string, opcional) - Data final YYYY-MM-DD

**Exemplo Request:**
```
GET /metrics/usage?company_id=clinica_abc&period=daily&start_date=2025-12-01&end_date=2025-12-10
```

**Response (200):**

```json
{
  "company_id": "clinica_abc",
  "period": "daily",
  "filters": {
    "start_date": "2025-12-01",
    "end_date": "2025-12-10"
  },
  "data": [
    {
      "period": "2025-12-10",
      "interactions": 150,
      "unique_sessions": 98,
      "tokens": {
        "input": 61800,
        "output": 11250,
        "total": 73050
      }
    },
    {
      "period": "2025-12-09",
      "interactions": 142,
      "unique_sessions": 89,
      "tokens": {
        "input": 58900,
        "output": 10680,
        "total": 69580
      }
    }
  ],
  "optimization_note": "Sistema otimizado: economia de 95% em tokens de prompt atraves de filtragem inteligente de agenda"
}
```

---

#### `GET /metrics/ranking`

Ranking de empresas por consumo de tokens.

**Query Parameters:**
- `period` (string) - `monthly` (default)
- `limit` (int) - Número de resultados (default: 10)

**Response (200):**

```json
{
  "period": "monthly",
  "ranking": [
    {
      "company_id": "clinica_grande",
      "total_tokens": 1250000,
      "total_interactions": 5200,
      "unique_sessions": 3100
    },
    {
      "company_id": "clinica_abc",
      "total_tokens": 850000,
      "total_interactions": 3500,
      "unique_sessions": 2200
    }
  ]
}
```

---

### **5. Sessões - Gerenciamento de Conversas**

#### `GET /sessions/{customer_id}`

Obtém histórico completo de uma sessão.

**Response (200):**

```json
{
  "session_id": "5521999887766",
  "company_id": "clinica_abc",
  "messages": [
    {
      "role": "user",
      "content": "Quero agendar",
      "timestamp": "2025-12-10T10:00:00Z",
      "metadata": {
        "sentiment": "positivo",
        "intent": "SCHEDULING"
      }
    },
    {
      "role": "assistant",
      "content": "Claro! Antes, preciso do seu nome completo e email.",
      "timestamp": "2025-12-10T10:00:05Z",
      "metadata": {
        "kanban_status": "Novo Lead",
        "directive_type": "normal"
      }
    }
  ],
  "rag_context_used": [
    {
      "question": "Como funciona o agendamento?",
      "relevance_score": 0.89,
      "used_at": "2025-12-10T10:00:05Z"
    }
  ],
  "summary": {
    "total_interactions": 5,
    "sentiment_history": ["positivo", "neutro", "positivo"],
    "intent_history": ["SCHEDULING", "INFO", "SCHEDULING"],
    "last_kanban_status": "Agendado",
    "rag_hits": 3
  },
  "customer_context": {
    "telefone": "5521999887766",
    "nome": "João Silva",
    "email": "joao@email.com",
    "is_data_complete": true
  },
  "created_at": "2025-12-10T10:00:00Z",
  "updated_at": "2025-12-10T10:30:00Z",
  "expires_at": "2026-01-09T10:00:00Z"
}
```

---

#### `DELETE /sessions/{customer_id}`

Remove sessão (reset de conversa).

**Response (200):**

```json
{
  "status": "success",
  "session_id": "5521999887766"
}
```

**Response (404):**

```json
{
  "detail": "Sessão não encontrada"
}
```

---

### **6. Sistema - Health Checks**

#### `GET /health`

Status básico da API.

**Response (200):**

```json
{
  "status": "healthy",
  "service": "scheduling-bot-v2-optimized",
  "version": "2.1.0"
}
```

---

#### `GET /health/ready`

Verifica se todos os serviços estão funcionando.

**Response (200):**

```json
{
  "status": "ready",
  "checks": {
    "mongodb": true,
    "openai": true
  }
}
```

**Response (503):**

```json
{
  "status": "not_ready",
  "checks": {
    "mongodb": true,
    "openai": false
  }
}
```

---

## Personalização por Empresa

### 15 Dimensões Configuráveis

#### 1. Identidade e Nicho
- `nicho_mercado`: Saúde, Estética, Jurídico, etc
- `nome_bot`: Nome do assistente virtual

#### 2. Segurança
- `enfase_confidencialidade`: Reforço de avisos de privacidade

#### 3. Vocabulário
- `vocabularios_especificos`: Dicionário de substituições
- `permitir_girias`: Uso de linguagem informal

#### 4. Personalidade
- `tom_voz`: Profissional, Amigável, Formal, Entusiasta
- `nivel_empatia`: Baixo, Médio, Alto
- `estilo_tratamento`: Você, Sr(a), Tu
- `uso_emojis`: nenhum, moderado, intenso

#### 5. Fluxo de Conversa
- `foco_conversa`: Objetivo principal do bot
- `extensao_respostas`: concisa, detalhada
- `estilo_persuasao`: suave, urgente

#### 6. Interação
- `reacao_erros`: Como reagir a inputs inválidos
- `frequencia_reforco_positivo`: Uso de feedback positivo
- `frequencia_cta`: Frequência de chamadas para ação
- `estilo_despedida`: Formato de encerramento

---

## Regras de Negócio

### 1. Barreira de Cadastro

O sistema bloqueia agendamento até ter:
- Nome completo
- Email válido

Comportamento:
- Solicita ambos na mesma mensagem
- Mantém persistência educada
- Ignora tentativas de agendamento sem cadastro completo

### 2. Protocolo de Oferta ("Ou/Ou")

Sempre apresentar opções concretas:

**Errado:** "Qual dia você prefere?"

**Correto:** "Tenho quinta às 14h ou sexta às 10h. Qual prefere?"

### 3. Protocolo Anti-Cancelamento

1. Primeira solicitação: Oferece reagendamento
2. Segunda solicitação: Processa cancelamento

### 4. Validação de Disponibilidade

- Sistema NUNCA inventa horários
- Usa apenas slots fornecidos na agenda
- Valida disponibilidade em tempo de filtragem

---

## Status Kanban

| Status | Descrição |
|--------|-----------|
| Novo Lead | Primeiro contato do cliente |
| Em Atendimento | Conversação em andamento |
| Agendado | Agendamento confirmado |
| Reagendamento | Cliente solicitou alteração de data/hora |
| Cancelado | Cliente cancelou agendamento |
| Handoff Humano | Cliente solicitou atendimento humano |
| Dúvida/Info | Cliente tem dúvidas gerais |

---

## Intents de Análise

| Intent | Descrição | Exemplo |
|--------|-----------|---------|
| SCHEDULING | Cliente quer marcar horário | "Quero marcar consulta" |
| RESCHEDULE | Cliente quer alterar horário existente | "Preciso remarcar" |
| CANCELLATION | Cliente quer cancelar | "Quero cancelar" |
| INFO | Cliente pede informações | "Quanto custa?" |
| HUMAN_HANDOFF | Cliente quer falar com humano | "Quero falar com atendente" |

---

## Sentimentos Detectados

| Sentimento | Descrição |
|------------|-----------|
| positivo | Cliente satisfeito, cooperativo |
| neutro | Cliente neutro, informativo |
| negativo | Cliente insatisfeito mas controlado |
| raiva | Cliente irritado, agressivo |
| ansioso | Cliente preocupado, urgente |
| confuso | Cliente perdido, não entende |
| triste | Cliente em dificuldade emocional |

---

## Estrutura do Projeto

```
scheduling-bot/
├── app/
│   ├── main.py                    # FastAPI app principal
│   ├── config.py                  # Configurações e variáveis de ambiente
│   │
│   ├── models/                    # Modelos Pydantic
│   │   ├── agent.py              # Status, Sentiments, Intents
│   │   ├── chat.py               # Request/Response
│   │   ├── company.py            # Configuração de empresa
│   │   ├── customer.py           # Perfil de cliente
│   │   ├── scheduling.py         # Agenda e disponibilidade
│   │   ├── usage.py              # Métricas de uso
│   │   └── knowledge.py          # Knowledge base (RAG)
│   │
│   ├── services/                  # Camada de serviços
│   │   ├── openai_service.py    # Integrações OpenAI
│   │   ├── company_service.py   # Gestão de empresas
│   │   ├── usage_service.py     # Tracking de tokens
│   │   ├── session_service.py   # Gestão de sessões
│   │   └── rag_service.py       # RAG e embeddings
│   │
│   ├── tools/                     # Tools do agente
│   │   ├── sentiment_tool.py    # Análise de sentimento
│   │   ├── intent_tool.py       # Análise de intenção
│   │   └── availability_tool.py # Filtragem de agenda
│   │
│   ├── agent/                     # LangGraph
│   │   ├── graph.py              # Definição do grafo
│   │   ├── state.py              # Estado do grafo
│   │   ├── prompts.py            # System prompts
│   │   └── nodes/                # Nós do grafo
│   │       ├── load_context.py
│   │       ├── check_integrity.py
│   │       ├── sentiment.py
│   │       ├── intent.py
│   │       ├── extract_entities.py
│   │       ├── filter_availability.py
│   │       ├── validate.py
│   │       ├── respond.py
│   │       ├── process_decision.py
│   │       └── save.py
│   │
│   ├── database/                  # Camada de dados
│   │   ├── mongodb.py            # Conexão MongoDB
│   │   └── cache.py              # Cache em memória
│   │
│   └── schemas/                   # Schemas MongoDB
│       ├── knowledge_base.py
│       └── chat_session.py
│
├── requirements.txt               # Dependências Python
├── .env.example                   # Template de variáveis
├── run.sh                         # Script de execução
└── README.md                      # Este arquivo
```

---

## Garantias do Sistema

### 1. Execução Obrigatória de Tools

O nó `validate` garante que:
- Tool sentiment foi executada
- Tool intent foi executada
- Ambas retornaram resultados válidos
- Ambas foram registradas em tools_called

Se qualquer validação falhar, o fluxo é interrompido com erro claro.

### 2. Validação de Diretivas

O nó `process_directives` garante que:
- `appointment_confirmation` tenha todos os 4 campos obrigatórios
- IDs sejam válidos e existam na agenda
- Nomes sejam enriquecidos automaticamente
- Diretiva seja revertida para `normal` se inválida

### 3. Economia de Tokens Garantida

- Agenda completa NUNCA é enviada ao LLM
- Apenas agenda filtrada (50-200 tokens) vai no prompt
- Extração de entidades usa regex (0 tokens)
- Cache reduz 90% das chamadas de tools

### 4. Tracking Completo

Todos os usos de LLM são registrados:
- Company ID
- Session ID
- Tokens de input/output
- Node que gerou o uso
- Timestamp completo
- Agregações por dia/semana/mês/ano

---

## Métricas de Performance

### Redução de Tokens

| Componente | Antes | Depois | Economia |
|-----------|-------|--------|----------|
| Agenda | 8000 | 150 | 98.1% |
| Extração entidades | 500 | 0 | 100% |
| Histórico | 2000 | 200 | 90% |
| Prompt base | 1500 | 300 | 80% |
| Contexto cliente | 300 | 50 | 83.3% |
| **TOTAL** | **12300** | **700** | **94.3%** |

### Custos Operacionais (GPT-4)

| Volume | Sistema Tradicional | Sistema Otimizado | Economia Mensal |
|--------|-------------------|------------------|-----------------|
| 1000 sessões/dia | $250/dia | $14/dia | $7.080/mês |
| 5000 sessões/dia | $1.250/dia | $70/dia | $35.400/mês |
| 10000 sessões/dia | $2.500/dia | $140/dia | $70.800/mês |

### Latência

- Sistema tradicional: 3-5 segundos
- Sistema otimizado: 1-2 segundos
- Redução: 60%

---

## Boas Práticas de Integração

### 1. Idempotência

Use `session_id` único e consistente para evitar duplicação.

### 2. Retry Logic

Implemente retry exponencial para erros 500:
```
Tentativa 1: 1s
Tentativa 2: 2s
Tentativa 3: 4s
Máximo: 3 tentativas
```

### 3. Timeout

Configure timeout de 30 segundos para requests.

### 4. Processamento de Diretivas

```python
def handle_bot_response(response):
    directives = response["directives"]

    if directives["type"] == "update_user":
        update_customer_data(directives["payload_update"])

    elif directives["type"] == "appointment_confirmation":
        appointment = directives["payload_appointment"]

        # Criar agendamento no sistema
        booking_id = create_booking(
            customer_id=response["cliente_id"],
            professional_id=appointment["profissional_id"],
            service_id=appointment["servico_id"],
            date=appointment["data"],
            time=appointment["hora"],
        )

        # Marcar slot como ocupado
        mark_slot_as_booked(appointment)

        # Enviar notificações
        send_confirmation_email(appointment)
        send_confirmation_sms(appointment)
        notify_professional(appointment)

        # Atualizar CRM
        update_kanban(response["cliente_id"], response["kanban_status"])
```

### 5. Atualização de Agenda

Mantenha a agenda sincronizada:
- Remova slots ocupados
- Adicione novos horários
- Atualize preços se necessário
- Desative profissionais em férias

### 6. Gestão do Knowledge Base (RAG)

```python
# Criar FAQs ao setup inicial
faqs = [
    {
        "question": "Como funciona o pagamento?",
        "answer": "Aceitamos cartão, PIX e dinheiro na recepção.",
        "category": "pagamento",
        "priority": 1
    },
    {
        "question": "Qual o horário de funcionamento?",
        "answer": "Segunda a sexta, 8h às 18h. Sábado, 8h às 12h.",
        "category": "informacao",
        "priority": 2
    }
]

# Upload em massa
response = requests.post(
    "http://localhost:8000/knowledge/bulk",
    json={
        "company_id": "clinica_abc",
        "entries": faqs
    }
)
```

---

## Troubleshooting

### Problema: Tokens muito altos

**Causa:** Sistema não está usando agenda filtrada

**Solução:** Verifique que `filtered_agenda` está sendo gerada no nó `filter_availability`

### Problema: LLM não confirma agendamento

**Causa:** Dados incompletos ou ambíguos

**Solução:**
- Verifique que cliente forneceu: serviço, profissional, data e hora
- Confira logs do nó `extract_entities`
- Valide que `filtered_agenda` tem opções

### Problema: Validação de tools falha

**Causa:** Tools não estão sendo executadas

**Solução:**
- Verifique ordem do grafo
- Confirme que sentiment e intent estão antes de validate
- Veja logs para identificar qual tool falhou

### Problema: IDs incorretos na confirmação

**Causa:** LLM não está usando IDs da agenda filtrada

**Solução:**
- Reforce no prompt o uso de IDs exatos
- Verifique que `filtered_agenda` está formatada corretamente
- Valide enriquecimento no `process_directives`

### Problema: RAG não está funcionando

**Causa:** Índice vetorial não foi criado no MongoDB Atlas

**Solução:**
1. Acesse MongoDB Atlas → Database → Search
2. Verifique se o índice `knowledge_vector_index` existe
3. Se não existir, crie conforme instruções na seção "Configuração do MongoDB Atlas"
4. Aguarde o índice ser construído (pode levar alguns minutos)
5. Teste com: `GET /knowledge?company_id=<id>`

### Problema: Erro "Vector search index not found"

**Causa:** Nome do índice incorreto ou índice ainda sendo construído

**Solução:**
- Verifique que o nome é exatamente `knowledge_vector_index`
- Aguarde a construção do índice (5-10 minutos após criação)
- Confira que a collection é `company_knowledge_base`

---

## Segurança

### Variáveis de Ambiente Sensíveis

Nunca commite:
- `OPENAI_API_KEY`
- `MONGODB_URI` (se contiver credenciais)
- Tokens de API de terceiros

### Rate Limiting (Recomendado)

Implemente limites:
- 100 requests/minuto por company_id
- 10 requests/segundo por session_id

### Validação de Input

Sistema valida automaticamente:
- Formato de emails
- Formato de datas (YYYY-MM-DD)
- Formato de horas (HH:MM)
- Existência de IDs na agenda

---

## Exemplos de Uso

### Exemplo 1: Primeira Interação - Sem Cadastro

**Request:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "5521999887766",
    "company": {
      "id": "clinica_abc",
      "nome": "Clínica ABC",
      "agenda": { ... }
    },
    "cliente": {
      "telefone": "5521999887766",
      "mensagem": "Quero agendar"
    }
  }'
```

**Response:**
```json
{
  "response_text": "Claro! Antes, preciso do seu nome completo e email para cadastro. Pode me passar?",
  "kanban_status": "Novo Lead",
  "directives": {
    "type": "normal"
  }
}
```

---

### Exemplo 2: Cliente Fornece Dados

**Request:**
```json
{
  "cliente": {
    "telefone": "5521999887766",
    "mensagem": "João Silva, joao@email.com"
  }
}
```

**Response:**
```json
{
  "response_text": "Perfeito João! Qual serviço você deseja agendar?",
  "kanban_status": "Em Atendimento",
  "directives": {
    "type": "update_user",
    "payload_update": {
      "nome": "João Silva",
      "email": "joao@email.com"
    }
  }
}
```

---

### Exemplo 3: Cliente Solicita Serviço

**Request:**
```json
{
  "cliente": {
    "nome": "João Silva",
    "email": "joao@email.com",
    "mensagem": "Limpeza de pele amanhã de manhã"
  }
}
```

**Response:**
```json
{
  "response_text": "Para Limpeza de Pele tenho: Ana na quinta às 9h ou Maria na sexta às 10h. Qual prefere?",
  "kanban_status": "Em Atendimento",
  "directives": {
    "type": "normal"
  }
}
```

---

### Exemplo 4: Cliente Confirma

**Request:**
```json
{
  "cliente": {
    "nome": "João Silva",
    "email": "joao@email.com",
    "mensagem": "Confirmo quinta às 9h com Ana"
  }
}
```

**Response:**
```json
{
  "response_text": "Agendado! Limpeza de Pele com Ana Ribeiro, quinta-feira 10/12 às 9h. Duração: 60min. Valor: R$ 180. Até lá!",
  "kanban_status": "Agendado",
  "directives": {
    "type": "appointment_confirmation",
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

---

## Roadmap

### v2.2 (Próximo)
- Suporte a múltiplos idiomas
- Webhooks para notificações em tempo real
- Dashboard de métricas

### v2.3
- Lembretes automáticos (SMS/Email)
- Feedback pós-atendimento
- A/B testing de prompts

### v3.0
- Multi-modal (voz + texto)
- IA preditiva para otimização de horários
- Integração nativa com WhatsApp Business

---

## Monitoramento e Logs

### Estrutura de Logs

Sistema gera logs estruturados em todos os nós:
```
[LOAD_CONTEXT] Iniciando sessão 5521999887766
[LOAD_CONTEXT] Histórico: 10 msgs, Recente: 4 msgs
[LOAD_CONTEXT] RAG: 3 FAQs recuperadas
[CHECK_INTEGRITY] Dados incompletos. Nome: True, Email: False
[SENTIMENT] Resultado: positivo (score: 80, confiança: alta)
[INTENT] Resultado: SCHEDULING - Cliente quer marcar horário
[EXTRACT] Entidades: {'service_name': 'limpeza de pele', 'time_preference': 'morning'}
[FILTER] 2 opções encontradas
[VALIDATE] ✅ Tools validadas com sucesso
[RESPOND] Tokens usados: 435 input + 77 output = 512 total
[PROCESS] Diretiva: appointment_confirmation | Kanban: Agendado
[SAVE_SESSION] Sessão salva com sucesso
```

### Níveis de Log

Configure via `.env`:
```bash
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR
```

- **DEBUG**: Todos os detalhes internos
- **INFO**: Fluxo principal e decisões
- **WARNING**: Situações atípicas mas controladas
- **ERROR**: Erros que requerem atenção

---

## Testes

### Teste de Importações

```bash
python test_import.py
```

Verifica que todos os módulos estão importando corretamente.

### Teste de Health Check

```bash
curl http://localhost:8000/health
```

**Response esperada:**
```json
{
  "status": "healthy",
  "service": "scheduling-bot-v2-optimized",
  "version": "2.1.0"
}
```

### Teste de Readiness

```bash
curl http://localhost:8000/health/ready
```

**Response esperada (tudo OK):**
```json
{
  "status": "ready",
  "checks": {
    "mongodb": true,
    "openai": true
  }
}
```

---

## Performance Tips

### 1. Use Cache Agressivamente

O sistema já implementa cache para:
- Análise de sentimento (1 hora)
- Análise de intenção (30 minutos)
- Busca RAG (1 hora)

### 2. Configure Batch de FAQs

Ao criar múltiplas FAQs, use o endpoint `/knowledge/bulk` ao invés de criar uma por uma:

```python
# ❌ Lento - 10 requests
for faq in faqs:
    requests.post("/knowledge", json=faq)

# ✅ Rápido - 1 request
requests.post("/knowledge/bulk", json={"entries": faqs})
```

### 3. Limite o Histórico

Configure quantas mensagens recentes são carregadas:

```python
# Em session_service.py
recent_history = await session_service.get_recent_history(
    session_id=state["session_id"],
    n=4  # Ajuste conforme necessário (4-10)
)
```

### 4. Otimize a Agenda

Mantenha a agenda compacta:
- Remova slots passados diariamente
- Limite visualização a 30 dias futuros
- Use IDs curtos (A1, S1) ao invés de UUIDs

---

## Suporte e Contribuição

### Documentação Adicional

- Documentação interativa: `http://localhost:8000/docs`
- Swagger UI: `http://localhost:8000/redoc`

### Issues e Bugs

Para reportar problemas:
1. Verifique logs em `logs/`
2. Inclua o `session_id` afetado
3. Compartilhe request/response completos
4. Mencione versão do Python e dependências

### Contribuindo

Pull requests são bem-vindos! Por favor:
1. Siga o estilo de código existente
2. Adicione testes para novas features
3. Atualize documentação
4. Mantenha commits descritivos

---

## FAQ

### P: Como adicionar novo idioma?

**R:** Atualmente o sistema opera em português. Para adicionar idiomas:
1. Traduza os prompts em `app/agent/prompts.py`
2. Adicione campo `language` na configuração da empresa
3. Implemente detecção automática ou permita escolha manual

### P: Posso usar outro LLM além do OpenAI?

**R:** Sim, mas requer modificações:
1. Substitua `openai_service.py` com novo provider
2. Ajuste formato de response
3. Teste compatibilidade com embeddings (512 dimensões)

### P: Como escalar para milhões de sessões?

**R:**
1. Use MongoDB Atlas com cluster M10+
2. Implemente Redis para cache distribuído
3. Configure load balancer
4. Ative MongoDB sharding por `company_id`
5. Considere microserviços para tools pesadas

### P: O sistema suporta WhatsApp direto?

**R:** Não nativamente. Integre com:
- Twilio WhatsApp API
- WhatsApp Business API oficial
- Plataformas como Wati ou Zenvia

### P: Como funciona o TTL das sessões?

**R:** Sessões expiram após 30 dias (configurável). MongoDB deleta automaticamente via índice TTL. Configure em `.env`:
```bash
SESSION_TTL_DAYS=30
```

---

**Versão:** 2.1.0
**Última Atualização:** Dezembro 2025