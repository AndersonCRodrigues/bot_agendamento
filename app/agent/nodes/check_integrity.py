import logging
from ..state import GraphState
from ...models.customer import CustomerProfile

logger = logging.getLogger(__name__)


async def check_integrity_node(state: GraphState) -> GraphState:

    try:
        logger.info("[CHECK_INTEGRITY] Verificando dados do cliente")

        profile_data = state.get("customer_profile")

        profile = CustomerProfile(**profile_data)

        has_name = bool(profile.nome and len(profile.nome.strip()) > 1)
        is_complete = has_name

        if not is_complete:
            logger.warning(
                f"[CHECK_INTEGRITY] Dados incompletos. "
                f"Nome: {bool(profile.nome)}, Email: {bool(profile.email)}"
            )
        else:
            logger.info(
                "[CHECK_INTEGRITY] Dados completos (nome presente). Fluxo liberado."
            )

        return {**state, "is_data_complete": is_complete}

    except Exception as e:
        logger.error(f"[CHECK_INTEGRITY] Erro: {e}", exc_info=True)
        return {**state, "is_data_complete": False, "error": str(e)}
