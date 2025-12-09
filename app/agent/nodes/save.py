import logging
from ..state import GraphState
from ...services import session_service
from ...schemas import ChatSession

logger = logging.getLogger(__name__)


async def save_session_node(state: GraphState) -> GraphState:
    """
    Nó 7: Salva sessão e registra interação

    Responsabilidades:
    1. Adicionar mensagens ao histórico (user + assistant)
    2. Atualizar summary da sessão
    3. Registrar uso do RAG (se relevante)
    4. (Futuro) Enviar webhook se notify=true
    """
    try:
        logger.info("[SAVE_SESSION] Salvando sessão")

        response = state["final_response"]

        # Helper para extrair valor seguro (string ou enum)
        def get_value(obj):
            """Extrai .value se for Enum, senão retorna o objeto"""
            return obj.value if hasattr(obj, "value") else obj

        # 1. Prepara mensagens para adicionar
        user_message = ChatSession.create_message(
            role="user",
            content=state["user_message"],
            metadata={
                "sentiment": get_value(state["sentiment_result"].sentiment),
                "intent": get_value(state["intent_result"].intent),
            },
        )

        assistant_message = ChatSession.create_message(
            role="assistant",
            content=response.reply,
            metadata={
                "notify": response.notify,
                "status": get_value(response.status),
                "kanban_status": (
                    get_value(response.update_kanban_status)
                    if response.update_kanban_status
                    else None
                ),
            },
        )

        # 2. Adiciona mensagens à sessão
        await session_service.append_messages(
            session_id=state["customer_id"], messages=[user_message, assistant_message]
        )

        logger.debug(
            f"[SAVE_SESSION] Mensagens adicionadas à sessão {state['customer_id']}"
        )

        # 3. Atualiza summary
        await session_service.update_summary(
            session_id=state["customer_id"],
            sentiment=get_value(state["sentiment_result"].sentiment),
            intent=get_value(state["intent_result"].intent),
            kanban_status=(
                get_value(response.update_kanban_status)
                if response.update_kanban_status
                else None
            ),
            rag_hit=len(state["rag_knowledge"]) > 0,
        )

        logger.debug("[SAVE_SESSION] Summary atualizado")

        # 4. Registra uso do RAG (se houve FAQs relevantes)
        if state["rag_knowledge"]:
            for faq in state["rag_knowledge"][:3]:  # Top 3
                await session_service.add_rag_usage(
                    session_id=state["customer_id"],
                    question=faq.question,
                    relevance_score=faq.relevance_score,
                )
            logger.debug(
                f"[SAVE_SESSION] {len(state['rag_knowledge'])} FAQs registradas"
            )

        # 5. TODO: Enviar webhook se notify=true
        if state["should_notify"]:
            logger.warning(
                f"[SAVE_SESSION] ⚠️ Webhook deveria ser enviado "
                f"(notify=true, status={get_value(response.status)})"  # ✅ CORRIGIDO
            )
            # Aqui entraria a lógica de webhook:
            # await webhook_service.send_notification(...)

        logger.info("[SAVE_SESSION] ✅ Sessão salva com sucesso")

        return state

    except Exception as e:
        logger.error(f"[SAVE_SESSION] Erro: {e}", exc_info=True)
        # Não falha o fluxo - apenas registra erro
        return {**state, "error": f"Erro save session: {e}"}
