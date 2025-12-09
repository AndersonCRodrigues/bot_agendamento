import logging
from langgraph.graph import StateGraph, END
from .state import GraphState
from .nodes import (
    load_context_node,
    check_integrity_node,
    analyze_sentiment_node,
    analyze_intent_node,
    validate_tools_node,
    agent_respond_node,
    process_directives_node,
    save_session_node,
)

logger = logging.getLogger(__name__)


def create_agent_graph():
    """
    Cria o grafo de execução do Bot de Agendamento.

    Fluxo:
    1. LOAD: Carrega agenda e perfil.
    2. INTEGRITY: Verifica se tem nome/email (define flag de bloqueio).
    3. TOOLS: Analisa sentimento e intenção.
    4. RESPOND: Gera resposta (Prompt decide se bloqueia ou agenda).
    5. PROCESS: Formata JSON de diretivas.
    6. SAVE: Salva histórico.
    """
    workflow = StateGraph(GraphState)

    # Adiciona os nós
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("check_integrity", check_integrity_node)
    workflow.add_node("sentiment", analyze_sentiment_node)
    workflow.add_node("intent", analyze_intent_node)
    workflow.add_node("validate", validate_tools_node)
    workflow.add_node("respond", agent_respond_node)
    workflow.add_node("process_directives", process_directives_node)
    workflow.add_node("save", save_session_node)

    # Define o fluxo (Edges)
    workflow.set_entry_point("load_context")

    workflow.add_edge("load_context", "check_integrity")
    workflow.add_edge("check_integrity", "sentiment")
    workflow.add_edge("sentiment", "intent")
    workflow.add_edge("intent", "respond")
    workflow.add_edge("respond", "process_directives")
    workflow.add_edge("process_directives", "save")
    workflow.add_edge("save", END)

    graph = workflow.compile()
    logger.info("✅ Grafo de Agendamento compilado com sucesso")
    return graph
