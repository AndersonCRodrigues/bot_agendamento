"""
Exemplos de uso da API do Bot de Cobrança
"""

import httpx
from datetime import date

# URL base da API
BASE_URL = "http://localhost:8000"


# ============================================================================
# 1. POPULAR KNOWLEDGE BASE (FAQs)
# ============================================================================


async def populate_knowledge_base():
    """Popula knowledge base com FAQs de exemplo"""

    company_id = "metlife_001"

    faqs = [
        {
            "question": "Como faço para gerar um boleto?",
            "answer": "O boleto será enviado pelo seu consultor via email ou WhatsApp. Você também pode solicitar uma segunda via através do nosso portal.",
            "category": "pagamento",
            "priority": 5,
        },
        {
            "question": "Quais são as opções de pagamento?",
            "answer": "Aceitamos: Boleto bancário, Pix (chave CNPJ) e Cartão de crédito. Todas as opções podem ser acessadas através do link que o consultor enviará.",
            "category": "pagamento",
            "priority": 5,
        },
        {
            "question": "Posso parcelar minha dívida?",
            "answer": "Sim! Oferecemos parcelamento em até 6x sem juros para quitação de débitos. Entre em contato com seu consultor para simular as melhores condições.",
            "category": "parcelamento",
            "priority": 4,
        },
        {
            "question": "Como atualizo os dados do meu cartão?",
            "answer": "Você pode atualizar os dados do cartão através do link seguro que o consultor enviará, ou ligando para nossa central de atendimento.",
            "category": "cartao",
            "priority": 3,
        },
        {
            "question": "Minha apólice foi cancelada?",
            "answer": "Apólices com mais de 80 dias de atraso correm risco de cancelamento. Porém, seu consultor pode verificar a situação atual e buscar alternativas para evitar o cancelamento.",
            "category": "cancelamento",
            "priority": 5,
        },
        {
            "question": "O que acontece se eu não pagar?",
            "answer": "Após 80 dias de atraso, a apólice pode ser cancelada e você perde a cobertura do seguro. É importante regularizar o quanto antes para manter sua proteção ativa.",
            "category": "consequencias",
            "priority": 4,
        },
        {
            "question": "Por que estou recebendo essa cobrança?",
            "answer": "Você está recebendo esta cobrança porque existem parcelas do seu seguro em atraso. Seu consultor pode detalhar exatamente quais parcelas estão pendentes.",
            "category": "duvidas",
            "priority": 5,
        },
        {
            "question": "Como funciona o Pix?",
            "answer": "Para pagar via Pix, use a chave CNPJ da Metlife que será fornecida pelo consultor. O pagamento é instantâneo e a quitação ocorre no mesmo dia.",
            "category": "pagamento",
            "priority": 4,
        },
    ]

    # Bulk insert
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/knowledge/bulk",
            json={"company_id": company_id, "entries": faqs},
            timeout=30.0,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['count']} FAQs criadas com sucesso!")
            print(f"IDs: {result['ids'][:3]}... (primeiros 3)")
        else:
            print(f"❌ Erro ao criar FAQs: {response.status_code}")
            print(response.text)


# ============================================================================
# 2. CONVERSA - Cliente Confuso
# ============================================================================


async def test_confused_customer():
    """Simula cliente confuso sobre cobrança"""

    request_data = {
        "company_id": "metlife_001",
        "customer_id": "cliente_001",
        "message": "Oi, recebi uma mensagem sobre uma cobrança mas não entendi",
        "customer_context": {
            "name": "João Silva",
            "policies": [
                {
                    "policy_number": "397910",
                    "total_due_value": 1500.50,
                    "total_due_installments": 3,
                    "due_installments": [
                        {
                            "number": 1,
                            "value": 500.17,
                            "due_date": "2024-08-30",
                            "days_overdue": 90,
                        },
                        {
                            "number": 2,
                            "value": 500.17,
                            "due_date": "2024-09-30",
                            "days_overdue": 60,
                        },
                        {
                            "number": 3,
                            "value": 500.16,
                            "due_date": "2024-10-30",
                            "days_overdue": 30,
                        },
                    ],
                }
            ],
            "total_due_value": 1500.50,
            "total_due_installments": 3,
            "consultant_name": "Maria Consultora",
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chat", json=request_data, timeout=30.0
        )

        if response.status_code == 200:
            result = response.json()
            print("\n" + "=" * 60)
            print("TESTE: Cliente Confuso")
            print("=" * 60)
            print(f"Mensagem: {request_data['message']}")
            print(f"\n🤖 Resposta: {result['response']['reply']}")
            print(f"\n📊 Metadata:")
            print(f"  - Sentimento: {result['metadata']['sentiment']}")
            print(f"  - Intenção: {result['metadata']['intent']}")
            print(f"  - Notify: {result['response']['notify']}")
            print(f"  - Status: {result['response']['status']}")
            print(f"  - Kanban: {result['response']['update_kanban_status']}")
            print(f"  - RAG Items: {result['metadata']['rag_items_retrieved']}")
            print(f"  - Tokens: {result['metadata']['tokens_used']['total']}")
        else:
            print(f"❌ Erro: {response.status_code}")
            print(response.text)


# ============================================================================
# 3. CONVERSA - Cliente Quer Pagar
# ============================================================================


async def test_positive_customer():
    """Simula cliente que quer pagar"""

    request_data = {
        "company_id": "metlife_001",
        "customer_id": "cliente_002",
        "message": "Vou pagar! Me envia o boleto por favor",
        "customer_context": {
            "name": "Maria Santos",
            "policies": [
                {
                    "policy_number": "398011",
                    "total_due_value": 850.00,
                    "total_due_installments": 2,
                    "due_installments": [
                        {
                            "number": 1,
                            "value": 425.00,
                            "due_date": "2024-09-15",
                            "days_overdue": 45,
                        },
                        {
                            "number": 2,
                            "value": 425.00,
                            "due_date": "2024-10-15",
                            "days_overdue": 15,
                        },
                    ],
                }
            ],
            "total_due_value": 850.00,
            "total_due_installments": 2,
            "consultant_name": "Pedro Consultor",
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chat", json=request_data, timeout=30.0
        )

        if response.status_code == 200:
            result = response.json()
            print("\n" + "=" * 60)
            print("TESTE: Cliente Quer Pagar (POSITIVA)")
            print("=" * 60)
            print(f"Mensagem: {request_data['message']}")
            print(f"\n🤖 Resposta: {result['response']['reply']}")
            print(f"\n📊 Metadata:")
            print(f"  - Sentimento: {result['metadata']['sentiment']}")
            print(f"  - Intenção: {result['metadata']['intent']}")
            print(f"  - Notify: {result['response']['notify']}")  # Deve ser TRUE
            print(
                f"  - Status: {result['response']['status']}"
            )  # Deve ser CUSTOMER_READY
            print(
                f"  - Kanban: {result['response']['update_kanban_status']}"
            )  # Deve ser ACORDO
        else:
            print(f"❌ Erro: {response.status_code}")


# ============================================================================
# 4. CONVERSA - Cliente Recusa
# ============================================================================


async def test_negative_customer():
    """Simula cliente que recusa pagamento"""

    request_data = {
        "company_id": "metlife_001",
        "customer_id": "cliente_003",
        "message": "Não vou pagar isso! Já cancelei esse seguro meses atrás!",
        "customer_context": {
            "name": "Carlos Oliveira",
            "policies": [
                {
                    "policy_number": "398112",
                    "total_due_value": 2100.00,
                    "total_due_installments": 4,
                    "due_installments": [
                        {
                            "number": 1,
                            "value": 525.00,
                            "due_date": "2024-07-30",
                            "days_overdue": 120,
                        }
                    ],
                }
            ],
            "total_due_value": 2100.00,
            "total_due_installments": 4,
            "consultant_name": "Ana Consultora",
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chat", json=request_data, timeout=30.0
        )

        if response.status_code == 200:
            result = response.json()
            print("\n" + "=" * 60)
            print("TESTE: Cliente Recusa (NEGATIVA)")
            print("=" * 60)
            print(f"Mensagem: {request_data['message']}")
            print(f"\n🤖 Resposta: {result['response']['reply']}")
            print(f"\n📊 Metadata:")
            print(
                f"  - Sentimento: {result['metadata']['sentiment']}"
            )  # Provavelmente RAIVA
            print(f"  - Intenção: {result['metadata']['intent']}")  # Deve ser NEGATIVA
            print(f"  - Notify: {result['response']['notify']}")  # Deve ser TRUE
            print(
                f"  - Status: {result['response']['status']}"
            )  # Deve ser NOTIFIED_CONSULTANT
            print(
                f"  - Kanban: {result['response']['update_kanban_status']}"
            )  # Deve ser RECUSA
        else:
            print(f"❌ Erro: {response.status_code}")


# ============================================================================
# 5. CONVERSA - Cliente Pede Humano
# ============================================================================


async def test_human_request():
    """Simula cliente que pede para falar com humano"""

    request_data = {
        "company_id": "metlife_001",
        "customer_id": "cliente_004",
        "message": "Quero falar com um atendente humano, por favor",
        "customer_context": {
            "name": "Paula Costa",
            "policies": [
                {
                    "policy_number": "398213",
                    "total_due_value": 650.00,
                    "total_due_installments": 1,
                    "due_installments": [
                        {
                            "number": 1,
                            "value": 650.00,
                            "due_date": "2024-10-20",
                            "days_overdue": 20,
                        }
                    ],
                }
            ],
            "total_due_value": 650.00,
            "total_due_installments": 1,
            "consultant_name": "Roberto Consultor",
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chat", json=request_data, timeout=30.0
        )

        if response.status_code == 200:
            result = response.json()
            print("\n" + "=" * 60)
            print("TESTE: Cliente Pede Humano")
            print("=" * 60)
            print(f"Mensagem: {request_data['message']}")
            print(f"\n🤖 Resposta: {result['response']['reply']}")
            print(f"\n📊 Metadata:")
            print(f"  - Notify: {result['response']['notify']}")  # Deve ser TRUE
            print(
                f"  - Status: {result['response']['status']}"
            )  # Deve ser NOTIFIED_CONSULTANT
            print(
                f"  - Kanban: {result['response']['update_kanban_status']}"
            )  # Deve ser HANDOFF_CONSULTOR
        else:
            print(f"❌ Erro: {response.status_code}")


# ============================================================================
# MAIN - Executa todos os testes
# ============================================================================


async def main():
    """Executa todos os testes em sequência"""

    print("🚀 Iniciando testes da API do Bot de Cobrança\n")

    # 1. Popula knowledge base
    print("📚 Populando Knowledge Base...")
    await populate_knowledge_base()

    # Aguarda um pouco para embeddings serem processados
    import asyncio

    await asyncio.sleep(2)

    # 2. Testes de conversa
    await test_confused_customer()
    await test_positive_customer()
    await test_negative_customer()
    await test_human_request()

    print("\n" + "=" * 60)
    print("✅ Todos os testes concluídos!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
