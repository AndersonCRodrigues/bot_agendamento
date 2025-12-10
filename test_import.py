"""
Script para testar importações e identificar problemas.
Execute: python test_imports.py
"""

print("Testando importações...")

try:
    print("1. Importando models.agent...")
    from app.models.agent import (
        AgentStatus,
        Sentiment,
        Intent,
        KanbanStatus,
        SentimentAnalysisResult,
        IntentAnalysisResult,
    )

    print("   OK")
except Exception as e:
    print(f"   ERRO: {e}")

try:
    print("2. Importando models.customer...")
    from app.models.customer import CustomerProfile

    print("   OK")
except Exception as e:
    print(f"   ERRO: {e}")

try:
    print("3. Importando models.chat...")
    from app.models.chat import ChatRequest, ChatResponse

    print("   OK")
except Exception as e:
    print(f"   ERRO: {e}")

try:
    print("4. Importando models.company...")
    from app.models.company import CompanyConfig

    print("   OK")
except Exception as e:
    print(f"   ERRO: {e}")

try:
    print("5. Importando models.scheduling...")
    from app.models.scheduling import FullAgenda, FilteredAgenda

    print("   OK")
except Exception as e:
    print(f"   ERRO: {e}")

try:
    print("6. Importando agent.state...")
    from app.agent.state import GraphState

    print("   OK")
except Exception as e:
    print(f"   ERRO: {e}")

try:
    print("7. Importando agent.graph...")
    from app.agent.graph import create_agent_graph

    print("   OK")
except Exception as e:
    print(f"   ERRO: {e}")

try:
    print("8. Importando main...")
    from app.main import app

    print("   OK")
except Exception as e:
    print(f"   ERRO: {e}")

print("\nTeste completo!")
