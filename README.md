# Bot Agendador Inteligente Multi-Nicho v2.1

Sistema de agendamento conversacional baseado em LangGraph com arquitetura otimizada para economia de tokens, personalização profunda por tenant e garantias de integridade de dados.

## Visão Geral

O sistema opera como uma Máquina de Estados Finitos (FSM) que converte leads em agendamentos confirmados através de conversação natural, respeitando regras de negócio rígidas e adaptando comportamento através de 6 dimensões configuráveis por empresa.

### Principais Características

- **Economia de 95-97% em tokens** através de filtragem inteligente de agenda
- **Arquitetura Zero-Write** - backend recebe apenas diretivas estruturadas
- **Personalização simplificada** - 6 dimensões de configuração essenciais
- **Garantias de integridade** - validação automática de dados cadastrais
- **Multi-nicho** - adaptável para saúde, estética, jurídico, serviços gerais
- **Multi-idioma** - suporte nativo para Português (BR), Inglês (US) e Espanhol (LA)
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

1. **LOAD_CONTEXT**: Carrega agenda completa + histórico + RAG no state
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

python -m venv venv
source venv/bin/activate

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

## Personalização por Empresa

### 6 Dimensões Configuráveis

A configuração de cada empresa é simplificada e focada no essencial:

```json
{
  "nicho_mercado": "Clínica Médica",
  "tom_voz": "Profissional",
  "idioma": "pt-BR",
  "uso_emojis": true,
  "frequencia_cta": "normal",
  "estilo_despedida": "Até logo!"
}
```

#### 1. Nicho de Mercado (`nicho_mercado`)
- **Tipo**: String livre
- **Obrigatório**: ✅ Sim (único campo sem padrão)
- **Exemplos**:
  - "Clínica Médica"
  - "Barbearia Premium"
  - "Estética Avançada"
  - "Consultório Odontológico"
  - "Escritório de Advocacia"
- **Impacto**: Contextualiza todo o prompt com vocabulário e tom específicos do setor

#### 2. Tom de Voz (`tom_voz`)
- **Tipo**: Enum fixo
- **Valores permitidos**:
  - `"Profissional"` - Formal, direto, sem intimidades (padrão)
  - `"Amigável"` - Cordial, próximo, acolhedor
  - `"Formal"` - Extremamente respeitoso, protocolado
  - `"Entusiasta"` - Animado, energético, motivador
- **Padrão**: `"Profissional"`
- **Exemplo de diferença**:
  - Profissional: "Olá! Posso agendar quinta às 14h ou sexta às 10h?"
  - Amigável: "Oi! Que tal quinta às 14h ou sexta às 10h? 😊"
  - Formal: "Prezado(a), disponibilizamos quinta-feira às 14h ou sexta-feira às 10h."
  - Entusiasta: "Ótimo! Tenho horários incríveis: quinta 14h ou sexta 10h!"

#### 3. Idioma (`idioma`)
- **Tipo**: Enum fixo
- **Valores permitidos**:
  - `"pt-BR"` - Português do Brasil (padrão)
  - `"en-US"` - English (United States)
  - `"es-LA"` - Español (Latinoamérica)
- **Padrão**: `"pt-BR"`
- **Impacto completo**:
  - System prompt traduzido nativamente
  - Mensagens de erro e validações
  - Formatação de datas e horários
  - Formatação de moeda
  - Validações de regex (nomes, emails)

**Exemplo de diferenças:**

| Aspecto | pt-BR | en-US | es-LA |
|---------|-------|-------|-------|
| Data | 10/12/2025 | 12/10/2025 | 10/12/2025 |
| Hora | 14h | 2 PM | 14h |
| Moeda | R$ 180,00 | $180.00 | $180.00 |
| Confirmação | "Confirmo" | "Confirm" | "Confirmo" |

#### 4. Uso de Emojis (`uso_emojis`)
- **Tipo**: Boolean
- **Valores**:
  - `true` - Usa emojis moderadamente (máx 1 por resposta)
  - `false` - Nunca usa emojis
- **Padrão**: `true`
- **Recomendação**:
  - `true` para nichos informais (barbearia, estética)
  - `false` para nichos formais (jurídico, médico)

#### 5. Frequência de CTA (`frequencia_cta`)
- **Tipo**: Enum fixo
- **Valores**:
  - `"minima"` - 1 CTA a cada 3-4 mensagens (conversação mais natural)
  - `"normal"` - 1 CTA a cada 2 mensagens (padrão, equilibrado)
  - `"maxima"` - 1 CTA em toda mensagem (vendas agressivas)
- **Padrão**: `"normal"`
- **CTA = Call To Action** (ex: "Confirma qual?", "Posso agendar?")

**Exemplo de diferença:**
```
[minima]
Bot: Tenho quinta às 14h ou sexta às 10h.
Cliente: Hum, deixa eu ver...
Bot: Sem pressa! Dá uma olhada e me avisa.

[normal - PADRÃO]
Bot: Tenho quinta às 14h ou sexta às 10h. Qual prefere?
Cliente: Hum, deixa eu ver...
Bot: Claro! Quando decidir, é só me avisar. Confirma qual?

[maxima]
Bot: Tenho quinta às 14h ou sexta às 10h. Confirma qual?
Cliente: Hum, deixa eu ver...
Bot: Quinta ou sexta? Qual você prefere agendar agora?
```

#### 6. Estilo de Despedida (`estilo_despedida`)
- **Tipo**: String livre
- **Padrão**: `"padrão"`
- **Exemplos personalizados**:
  - Informal: "Até logo! 👋"
  - Formal: "Atenciosamente, Equipe [Nome]"
  - Regional: "Tchau, tchau!"
  - Profissional saúde: "Cuide-se bem!"
  - Fitness: "Bons treinos!"

---

### Configurações Fixas (Não Personalizáveis)

Para garantir qualidade e consistência, estas configurações são **hard-coded** no sistema:

#### 1. **Confidencialidade: Sempre Ativa**
- Disclaimer automático de privacidade (LGPD/GDPR)
- Adaptado ao idioma configurado:
  - 🇧🇷 "Suas informações são confidenciais e protegidas pela LGPD."
  - 🇺🇸 "Your information is confidential and protected by privacy laws."
  - 🇪🇸 "Su información es confidencial y protegida por las leyes de privacidad."

#### 2. **Nível de Empatia: Sempre Alto**
- O bot sempre demonstra empatia e compreensão
- Reconhece frustração do cliente
- Oferece alternativas antes de negar
- Não pode ser configurado como "baixo" ou "médio"

#### 3. **Extensão de Respostas: Sempre Concisa**
- Máximo de 2-3 frases por resposta
- Objetivo e direto ao ponto
- Evita explicações longas não solicitadas

#### 4. **Estilo de Persuasão: Sempre Suave**
- Nunca usa técnicas de pressão
- Não cria senso de urgência artificial
- Não usa frases como "última vaga", "só hoje"

#### 5. **Reação a Erros: Sempre Educada**
- Nunca culpa o cliente por input incorreto
- Oferece ajuda de forma construtiva
- Reformula a pergunta para facilitar

#### 6. **Tratamento: Sempre "Você"**
- Usa "você" em português
- Usa "you" em inglês
- Usa "tú/usted" em espanhol (adaptado ao tom)
- Não usa "Sr(a)", "V.Sa.", "tu"

#### 7. **Gírias: Sempre Desativadas**
- Linguagem clara e profissional
- Evita regionalismo excessivo
- Mantém compreensão universal

---

### Exemplos de Configuração por Nicho

#### Clínica Médica
```json
{
  "nicho_mercado": "Clínica Médica",
  "tom_voz": "Formal",
  "idioma": "pt-BR",
  "uso_emojis": false,
  "frequencia_cta": "minima",
  "estilo_despedida": "Cuide-se bem!"
}
```

#### Barbearia Moderna
```json
{
  "nicho_mercado": "Barbearia Premium",
  "tom_voz": "Amigável",
  "idioma": "pt-BR",
  "uso_emojis": true,
  "frequencia_cta": "normal",
  "estilo_despedida": "Até a próxima, parça! ✂️"
}
```

#### Escritório de Advocacia
```json
{
  "nicho_mercado": "Escritório de Advocacia",
  "tom_voz": "Formal",
  "idioma": "pt-BR",
  "uso_emojis": false,
  "frequencia_cta": "minima",
  "estilo_despedida": "Atenciosamente, Dr. Silva & Associados"
}
```

#### Spa Internacional
```json
{
  "nicho_mercado": "Luxury Spa & Wellness",
  "tom_voz": "Profissional",
  "idioma": "en-US",
  "uso_emojis": true,
  "frequencia_cta": "normal",
  "estilo_despedida": "Relax and rejuvenate! 🧘"
}
```

#### Clínica de Estética Latina
```json
{
  "nicho_mercado": "Clínica de Estética",
  "tom_voz": "Entusiasta",
  "idioma": "es-LA",
  "uso_emojis": true,
  "frequencia_cta": "maxima",
  "estilo_despedida": "¡Hasta pronto, bella! 💆"
}
```

---

## 📡 API Reference - Endpoints Principais

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
        }
      },
      "services": {
        "S1": {
          "id": "S1",
          "name": "Limpeza de Pele",
          "duration": 60,
          "price": 180
        }
      },
      "availability": {
        "A1": {
          "S1": {
            "2025-12-10": ["08:00", "09:00", "10:00"]
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

**Response:**

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

### **2. Companies - Configuração de Empresas**

#### `POST /companies/{company_id}/config`

Cria ou atualiza configuração comportamental de uma empresa.

**Path Parameters:**
- `company_id` (string) - ID único da empresa

**Request Body:**

```json
{
  "nicho_mercado": "Clínica Médica",
  "tom_voz": "Profissional",
  "idioma": "pt-BR",
  "uso_emojis": true,
  "frequencia_cta": "normal",
  "estilo_despedida": "Até logo!"
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
    "tom_voz": "Profissional",
    "idioma": "pt-BR",
    "uso_emojis": true,
    "frequencia_cta": "normal",
    "estilo_despedida": "Até logo!"
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

#### `GET /sessions/{session_id}`

Obtém histórico completo de uma sessão.

**Path Parameters:**
- `session_id` (string) - ID da sessão (normalmente o telefone do cliente)

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

**Response (404):**

```json
{
  "detail": "Sessao 5521999887766 nao encontrada"
}
```

---

#### `DELETE /sessions/{session_id}`

Remove sessão (reset de conversa).

**Path Parameters:**
- `session_id` (string) - ID da sessão

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
  "detail": "Sessao 5521999887766 nao encontrada"
}
```

**Caso de Uso:**
- Resetar conversa problemática
- Limpar histórico para testes
- Cliente solicitou exclusão de dados (LGPD)

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

## 📋 Exemplos Detalhados por Tipo de Diretiva

### **Diretiva 1: `normal` - Conversação em Andamento**

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

### **Diretiva 2: `update_user` - Atualização de Cadastro**

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

### **Diretiva 3: `appointment_confirmation` - Agendamento Confirmado**

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

## ❌ Exemplos de Casos INVÁLIDOS para `appointment_confirmation`

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

## 🔄 Fluxo Completo: Do Primeiro Contato ao Agendamento

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

### 1. Barreira de Cadastro

O sistema bloqueia agendamento até ter:
- Nome completo
- Email válido

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
| Reagendamento | Cliente solicitou alteração |
| Cancelado | Cliente cancelou |
| Handoff Humano | Cliente solicitou atendente |
| Dúvida/Info | Cliente tem dúvidas gerais |

---

## Intents de Análise

| Intent | Descrição | Exemplo |
|--------|-----------|---------|
| SCHEDULING | Cliente quer marcar horário | "Quero marcar consulta" |
| RESCHEDULE | Cliente quer alterar horário | "Preciso remarcar" |
| CANCELLATION | Cliente quer cancelar | "Quero cancelar" |
| INFO | Cliente pede informações | "Quanto custa?" |
| HUMAN_HANDOFF | Cliente quer falar com humano | "Quero atendente" |

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

## Suporte Multi-Idioma

### Português (pt-BR)
- Validações de nome (acentos)
- Formatação de datas: DD/MM/YYYY
- Moeda: R$
- Horário: 24h

### English (en-US)
- Name validations (ASCII)
- Date format: MM/DD/YYYY
- Currency: $
- Time: 12h AM/PM

### Español (es-LA)
- Validaciones de nombre (tildes)
- Formato de fecha: DD/MM/YYYY
- Moneda: $
- Horario: 24h

---

## Métricas de Performance

### Redução de Tokens

| Componente | Antes | Depois | Economia |
|-----------|-------|--------|----------|
| Agenda | 8000 | 150 | 98.1% |
| Extração entidades | 500 | 0 | 100% |
| Histórico | 2000 | 200 | 90% |
| Prompt base | 1500 | 300 | 80% |
| **TOTAL** | **12300** | **700** | **94.3%** |

### Custos Operacionais (GPT-4)

| Volume | Tradicional | Otimizado | Economia/mês |
|--------|-------------|-----------|--------------|
| 1000 sessões/dia | $250/dia | $14/dia | $7.080 |
| 5000 sessões/dia | $1.250/dia | $70/dia | $35.400 |
| 10000 sessões/dia | $2.500/dia | $140/dia | $70.800 |

---

## Troubleshooting

### Problema: Sessão não encontrada (404)

**Sintoma:**
```bash
curl http://localhost:8000/sessions/5521999887766
# Response: {"detail": "Sessao 5521999887766 nao encontrada"}
```

**Causas Possíveis:**
1. Session ID incorreto ou com formatação errada
2. Sessão expirou (TTL de 30 dias padrão)
3. Sessão nunca foi criada (nenhuma interação no `/chat`)
4. MongoDB não está conectado ou inacessível

**Soluções:**

**1. Verificar se session_id está correto:**
```bash
curl http://localhost:8000/sessions/{session_id_exato}
```

**2. Verificar se sessão existe no MongoDB:**
```javascript
// MongoDB shell
db.chat_sessions.findOne({session_id: "5521999887766"})
```

**3. Verificar TTL (Time To Live):**
```javascript
// Verificar se sessão expirou
db.chat_sessions.findOne({
  session_id: "5521999887766",
  expires_at: {$gte: new Date()}
})
```

**4. Criar nova sessão via /chat:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{...payload completo...}'
```

**5. Verificar conexão MongoDB:**
```bash
curl http://localhost:8000/health/ready
# Deve retornar: {"status": "ready", "checks": {"mongodb": true}}
```

### Problema: Tokens muito altos (>3000 por request)

**Sintoma:**
```json
{
  "cost_info": {
    "total_tokens": 8500,
    "input_tokens": 8200,
    "output_tokens": 300
  }
}
```

**Causa:** Sistema não está usando agenda filtrada corretamente.

**Diagnóstico:**
1. Verifique logs do nó `filter_availability`:
```
[FILTER] 0 opções encontradas  ❌ PROBLEMA
[FILTER] 3 opções encontradas  ✅ OK
```

2. Verifique se `extracted_entities` tem dados:
```python
# Deve conter algo como:
{
  "service_name": "limpeza de pele",
  "time_preference": "morning"
}
```

**Soluções:**

**1. Agenda vazia ou mal formatada:**
```json
// Verifique se request tem estrutura correta:
{
  "company": {
    "agenda": {
      "professionals": {...},
      "services": {...},
      "availability": {...}
    }
  }
}
```

**2. Intent não é SCHEDULING:**
```python
# Se intent=INFO, não filtra agenda
# Solução: Ajuste mensagem do cliente para ser mais clara sobre agendamento
```

**3. Extração de entidades falhou:**
```python
# Verifique regex patterns em extract_entities_node.py
# Service/professional não foram detectados
```

**4. Force modo debug:**
```python
# Em filter_availability_node.py, adicione:
logger.setLevel(logging.DEBUG)
```

### Problema: LLM não confirma agendamento

**Sintoma:**
Cliente diz "Confirmo quinta às 9h" mas bot retorna `type: "normal"` ao invés de `appointment_confirmation`.

**Causas:**

**1. Dados incompletos (mais comum):**
```python
# Cliente não especificou: profissional, serviço, data OU hora
# Solução: Bot deve perguntar o que falta
```

**2. Agenda filtrada vazia:**
```python
# filtered_agenda.options = []
# Solução: Verifique disponibilidade real na agenda
```

**3. Cliente não usou palavra de confirmação:**
```
❌ "E quinta?"  # Pergunta, não confirmação
❌ "Hum, quinta tá bom"  # Ambíguo
✅ "Confirmo quinta"
✅ "Pode ser quinta"
✅ "Fechado"
```

**Soluções:**

**1. Verificar logs do nó `respond`:**
```
[RESPOND] Gerando resposta do agente
[RESPOND] Agenda context: "AGENDA: Cliente perguntou sobre..."  ❌
[RESPOND] Agenda context: "Serviço: Limpeza de Pele..."  ✅
```

**2. Verificar extracted_entities:**
```json
{
  "service_name": "limpeza",  // ✅ OK
  "professional_name": "ana",  // ✅ OK
  "date_specific": "2025-12-10",  // ✅ OK
  "time_preference": "morning"  // ⚠️ Falta hora exata
}
```

**3. Ajustar prompt se necessário:**
```python
# Em prompts.py, reforçar regra:
"Para gerar appointment_confirmation, cliente DEVE ter confirmado EXPLICITAMENTE"
```

### Problema: Validação de tools falha

**Sintoma:**
```
[VALIDATE] ❌ VALIDAÇÃO FALHOU:
  - ERRO: Sentiment analysis não foi executada
  - ERRO: Intent analysis não foi executada
```

**Causa:** Tools sentiment/intent não estão sendo executadas antes do nó `validate`.

**Diagnóstico:**

**1. Verificar ordem do grafo:**
```python
# Em graph.py, ordem DEVE ser:
workflow.add_edge("check_integrity", "sentiment")  # ✅
workflow.add_edge("sentiment", "intent")  # ✅
workflow.add_edge("intent", "extract_entities")  # ✅
workflow.add_edge("extract_entities", "filter_availability")  # ✅
workflow.add_edge("filter_availability", "validate")  # ✅
```

**2. Verificar se tools retornam resultado:**
```python
# Em sentiment.py e intent.py:
return {
    **state,
    "sentiment_result": result,  # ✅ Deve estar presente
    "sentiment_analyzed": True,  # ✅ Flag obrigatória
}
```

**Soluções:**

**1. Verificar imports:**
```python
from ...tools import sentiment_tool, intent_tool  # ✅
```

**2. Verificar que tools_called é populado:**
```python
# Cada tool deve adicionar:
"tools_called": ["sentiment"]  # sentiment_node
"tools_called": ["intent"]  # intent_node
```

**3. Verificar logs de cada nó:**
```
[SENTIMENT] Analisando sentimento  ✅
[SENTIMENT] Resultado: positivo (score: 80)  ✅
[INTENT] Analisando intenção  ✅
[INTENT] Resultado: SCHEDULING  ✅
[VALIDATE] ✅ Tools validadas com sucesso  ✅
```

### Problema: IDs incorretos na confirmação

**Sintoma:**
```json
{
  "payload_appointment": {
    "profissional_id": "Ana Ribeiro",  // ❌ Deve ser "A1"
    "servico_id": "Limpeza de Pele"  // ❌ Deve ser "S1"
  }
}
```

**Causa:** LLM está usando nomes ao invés de IDs.

**Soluções:**

**1. Reforçar no prompt:**
```python
# Em prompts.py:
"VALIDAÇÃO DE IDS (CRÍTICO)
- profissional_id: use o ID EXATO da agenda (ex: 'A1', 'A2')
- servico_id: use o ID EXATO da agenda (ex: 'S1', 'S2')
- NÃO use nomes, use APENAS IDs"
```

**2. Verificar agenda filtrada:**
```python
# Em filtered_agenda, IDs devem estar visíveis:
{
  "options": [
    {
      "professional": "Ana Ribeiro",
      "professional_id": "A1",  # ✅ ID presente
      "service_id": "S1"  # ✅ ID presente
    }
  ]
}
```

**3. Usar process_directives para validar:**
```python
# O nó já valida e reverte para "normal" se IDs inválidos
# Verifique logs:
[PROCESS] Profissional 'Ana Ribeiro' não encontrado, revertendo para normal  ❌
[PROCESS] Diretiva validada com sucesso  ✅
```

### Problema: RAG não está funcionando

**Sintoma:**
```python
# Logs mostram:
[RAG] ⚠️ Nenhuma FAQ encontrada para company_id=clinica_abc
[RAG] ❌ Vector search falhou: Vector search index not found
```

**Causas:**

**1. Índice vetorial não foi criado no MongoDB Atlas (mais comum)**

**Solução:**
1. Acesse MongoDB Atlas → Database → Search
2. Verifique se o índice `knowledge_vector_index` existe
3. Se não existir, crie conforme instruções na seção "Configuração do MongoDB Atlas Vector Search Index"
4. Aguarde o índice ser construído (5-10 minutos)
5. Teste novamente

**2. Nome do índice incorreto:**
```javascript
// Deve ser exatamente:
"name": "knowledge_vector_index"

// Não pode ser:
"name": "vector_search"  // ❌
"name": "knowledge_index"  // ❌
```

**3. Collection incorreta:**
```javascript
// Índice deve estar na collection:
"company_knowledge_base"

// Não em:
"knowledge"  // ❌
"faqs"  // ❌
```

**4. Nenhuma FAQ cadastrada:**
```bash
# Verificar no MongoDB:
db.company_knowledge_base.countDocuments({
  company_id: "clinica_abc",
  is_active: true
})
# Deve retornar > 0
```

**Solução: Cadastrar FAQs:**
```bash
curl -X POST http://localhost:8000/knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "clinica_abc",
    "question": "Como funciona o pagamento?",
    "answer": "Aceitamos cartão, PIX e dinheiro.",
    "category": "pagamento",
    "priority": 3
  }'
```

**Diagnóstico avançado:**

**1. Testar busca vetorial diretamente:**
```javascript
// No MongoDB shell:
db.company_knowledge_base.aggregate([
  {
    $vectorSearch: {
      index: "knowledge_vector_index",
      path: "embedding",
      queryVector: [...],  // 512 dimensões
      numCandidates: 10,
      limit: 5
    }
  }
])
```

**2. Verificar logs detalhados:**
```python
# Em rag_service.py, linha do vector_search:
logger.setLevel(logging.DEBUG)
```

**3. Testar fallback search:**
```python
# Se vector search falhar, sistema usa regex fallback
# Verifique se FAQs aparecem mesmo sem índice:
[RAG FALLBACK] ✅ 3 FAQs encontradas
```

### Problema: Erro "Vector search index not found"

**Sintoma:**
```
pymongo.errors.OperationFailure: $vectorSearch is not allowed or the request was malformed
```

**Causa:** Índice vetorial não existe ou está com configuração errada.

**Solução definitiva:**

**1. Verificar se índice existe:**
```
MongoDB Atlas → Database → Search → Indexes
Procure por: "knowledge_vector_index"
```

**2. Deletar índice antigo (se existir com config errada):**
```
Click no índice → Delete
```

**3. Criar índice correto:**
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

**4. Aplicar na collection correta:**
- Database: `scheduling_bot`
- Collection: `company_knowledge_base`

**5. Aguardar build (5-10 minutos):**
```
Status: Building → Ready
```

**6. Testar:**
```bash
curl http://localhost:8000/knowledge?company_id=clinica_abc
```

### Problema: Multi-idioma não funciona

**Sintoma:**
Configurei `idioma: "en-US"` mas bot responde em português.

**Causa:** Configuração não está sendo lida corretamente.

**Diagnóstico:**

**1. Verificar config no banco:**
```javascript
db.companies.findOne({company_id: "clinica_abc"})
// Deve ter: config.idioma = "en-US"
```

**2. Verificar logs:**
```
[RESPOND] Gerando resposta do agente
# Deve mostrar qual idioma está usando
```

**Solução:**

**1. Atualizar config:**
```bash
curl -X POST http://localhost:8000/companies/clinica_abc/config \
  -H "Content-Type: application/json" \
  -d '{"nicho_mercado": "Medical Clinic", "idioma": "en-US"}'
```

**2. Usar config_override no request:**
```json
{
  "company": {
    "config_override": {
      "nicho_mercado": "Medical Clinic",
      "idioma": "en-US"
    }
  }
}
```

**3. Verificar se prompt está traduzido:**
```python
# Em prompts.py, função build_optimized_prompt:
if idioma == "en-US":
    return _build_prompt_en_us(...)  # ✅
```

---

## Segurança

### Variáveis de Ambiente Sensíveis

Nunca commite:
- `OPENAI_API_KEY`
- `MONGODB_URI` (se contiver credenciais)

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

## Roadmap

### v2.2 (Próximo)
- Webhooks para notificações em tempo real
- Dashboard de métricas
- Migration automática de configs antigas

### v2.3
- Lembretes automáticos (SMS/Email)
- Feedback pós-atendimento
- A/B testing de prompts

### v3.0
- Multi-modal (voz + texto)
- IA preditiva para otimização de horários
- Integração nativa com WhatsApp Business

---

## FAQ

### P: Como adicionar novo idioma?

**R:** Edite `app/agent/prompts.py`:
1. Adicione novo idioma no enum: `Literal["pt-BR", "en-US", "es-LA", "fr-FR"]`
2. Crie função `_build_prompt_fr_fr()`
3. Adicione tradução em `CONFIDENTIALITY_DISCLAIMER`
4. Implemente funções auxiliares `_get_*_rule_fr()`

### P: Como mudar valores padrão?

**R:** Edite `app/models/company.py`:
```python
tom_voz: Literal[...] = "Amigável"
uso_emojis: bool = False
```

---

**Versão:** 2.1.0
**Última Atualização:** Dezembro 2025