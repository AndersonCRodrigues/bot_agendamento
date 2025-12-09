import logging
from ..state import GraphState

logger = logging.getLogger(__name__)


async def check_integrity_node(state: GraphState) -> GraphState:
    """
    Nó de Barreira: Verifica se o cadastro está completo.

    Lógica:
    1. Analisa o CustomerProfile.
    2. Se faltar dados (nome/email), define is_data_complete = False.
    3. Isso vai ativar o 'Protocolo de Bloqueio' no prompt depois.
    """
    try:
        logger.info("[CHECK_INTEGRITY] Verificando dados do cliente")

        profile = state.get("customer_profile")

        # O método check_completion() já foi definido no model CustomerProfile
        # Ele verifica se tem Nome E Email
        is_complete = profile.check_completion()

        if not is_complete:
            logger.warning(
                f"[CHECK_INTEGRITY] ⚠️ Dados incompletos. Faltando: Nome={bool(profile.nome)}, Email={bool(profile.email)}"
            )
        else:
            logger.info("[CHECK_INTEGRITY] ✅ Dados completos. Fluxo liberado.")

        return {**state, "is_data_complete": is_complete}

    except Exception as e:
        logger.error(f"[CHECK_INTEGRITY] Erro: {e}", exc_info=True)
        return {**state, "is_data_complete": False, "error": str(e)}
