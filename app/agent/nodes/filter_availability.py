import logging
from ..state import GraphState
from ...tools.availability_tool import availability_tool
from ...models.scheduling import AvailabilitySearchParams

logger = logging.getLogger(__name__)


async def filter_availability_node(state: GraphState) -> GraphState:
    """
    Filtra a agenda com base nas entidades extraídas e intenção.

    CRÍTICO: Este nó NÃO usa LLM e NÃO consome tokens.
    Ele apenas processa a agenda internamente.

    Economia: ~8000 tokens por request
    """
    try:
        logger.info("[FILTER] Filtrando disponibilidade")

        intent = state["intent_result"].intent
        entities = state.get("extracted_entities", {})

        if intent not in ["SCHEDULING", "RESCHEDULE"]:
            logger.info("[FILTER] Intent não requer filtragem de agenda")
            return {**state, "filtered_agenda": None}

        search_params = AvailabilitySearchParams(
            service_name=entities.get("service_name"),
            professional_name=entities.get("professional_name"),
            date=entities.get("date_specific"),
            time_preference=entities.get("time_preference"),
            max_results=3,
        )

        logger.info(f"[FILTER] Params: {search_params.model_dump()}")

        filtered = availability_tool.filter_availability(
            agenda=state["full_agenda"], params=search_params
        )

        if filtered.options:
            logger.info(f"[FILTER] {len(filtered.options)} opções encontradas")
        else:
            logger.warning("[FILTER] Nenhuma opção disponível")

        return {**state, "filtered_agenda": filtered}

    except Exception as e:
        logger.error(f"[FILTER] Erro ao filtrar: {e}", exc_info=True)
        return {**state, "filtered_agenda": None, "error": str(e)}
