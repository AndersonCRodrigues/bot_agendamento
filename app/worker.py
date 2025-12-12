import logging
import httpx
from datetime import datetime
from arq.connections import RedisSettings
from app.database import mongodb
from app.services import session_service, company_service
from app.agent import create_agent_graph, GraphState
from app.models import CustomerProfile, ChatResponse
from app.config import settings

logger = logging.getLogger(__name__)


async def startup(ctx):
    await mongodb.connect()
    logger.info("Worker: Conectado ao MongoDB")


async def shutdown(ctx):
    await mongodb.close()
    logger.info("Worker: Desconectado do MongoDB")


async def delayed_response_task(
    ctx, session_id: str, user_message: str, company_payload: dict
):
    try:
        logger.info(f"[WORKER] Processando mensagem atrasada: {session_id}")

        session = await session_service.get_session(session_id)
        if not session:
            logger.error(f"[WORKER] Sessão não encontrada: {session_id}")
            return

        # Validações de estado (Pausa e Owner)
        if session.get("paused_until") and session["paused_until"] > datetime.now():
            logger.info(
                "[WORKER] Bloqueio renovado pelo Owner. Abortando resposta automática."
            )
            return

        if session.get("last_sender_type") != "user":
            logger.info(
                "[WORKER] Última mensagem não é do usuário. Owner assumiu. Abortando."
            )
            return

        # Carrega configuração da empresa
        company_id = company_payload.get("id")
        if config_override := company_payload.get("config_override"):
            company_config = config_override
        else:
            config_obj = await company_service.get_config(company_id)
            company_config = config_obj.model_dump()

        customer_data = session.get("customer_context", {})
        customer_profile = CustomerProfile(
            telefone=customer_data.get("telefone"),
            nome=customer_data.get("nome"),
            email=customer_data.get("email"),
            is_data_complete=customer_data.get("is_data_complete", False),
        )

        initial_state = GraphState(
            company_id=company_id,
            session_id=session_id,
            user_message=user_message,
            company_config=company_config,
            customer_profile=customer_profile.model_dump(),
            company_agenda=company_payload.get("agenda"),
            full_agenda=None,
            filtered_agenda=None,
            chat_history=[],
            recent_history=[],
            sentiment_result=None,
            intent_result=None,
            sentiment_analyzed=False,
            intent_analyzed=False,
            tools_validated=False,
            is_data_complete=customer_profile.is_data_complete,
            extracted_entities={},
            final_response=None,
            tools_called=[],
            prompt_tokens=0,
            completion_tokens=0,
            error=None,
            llm_response_raw={},
        )

        graph = create_agent_graph()
        final_state = await graph.ainvoke(initial_state)

        if final_state.get("final_response"):
            response_obj: ChatResponse = final_state["final_response"]

            payload = response_obj.model_dump(mode="json")

            headers = {
                "X-Webhook-Token": settings.WEBHOOK_SECRET_TOKEN,
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                logger.info(
                    f"[WORKER] Enviando webhook para: {settings.MAIN_BACKEND_WEBHOOK_URL}"
                )

                response = await client.post(
                    settings.MAIN_BACKEND_WEBHOOK_URL,
                    json=payload,
                    headers=headers,
                    timeout=15.0,
                )

                if response.status_code == 200:
                    logger.info(
                        f"[WORKER] ✅ Webhook entregue com sucesso para {session_id}"
                    )
                else:
                    logger.error(
                        f"[WORKER] ❌ Falha ao entregar webhook. Status: {response.status_code}, Body: {response.text}"
                    )

    except Exception as e:
        logger.error(f"[WORKER] Erro ao processar task: {e}", exc_info=True)


class WorkerSettings:
    functions = [delayed_response_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
