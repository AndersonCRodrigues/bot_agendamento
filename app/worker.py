import logging
import httpx
from datetime import datetime
from arq.connections import RedisSettings
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from app.database import mongodb
from app.services import session_service, company_service
from app.agent import create_agent_graph, GraphState
from app.models import CustomerProfile, ChatResponse
from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def startup(ctx):
    await mongodb.connect()
    logger.info("🟢 Worker: Conectado ao MongoDB")


async def shutdown(ctx):
    await mongodb.close()
    logger.info("🔴 Worker: Desconectado do MongoDB")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def send_webhook(url: str, payload: dict, headers: dict):
    async with httpx.AsyncClient() as client:
        logger.info(f"[WEBHOOK] Tentando enviar para {url}")
        response = await client.post(
            url,
            json=payload,
            headers=headers,
            timeout=15.0,
        )
        response.raise_for_status()
        logger.info(f"[WEBHOOK] ✅ Sucesso! Status: {response.status_code}")
        return response


async def save_to_dlq(
    session_id: str,
    payload: dict,
    error: str,
    attempts: int,
):
    try:
        db = mongodb.get_database()
        await db.webhook_failures.insert_one(
            {
                "session_id": session_id,
                "payload": payload,
                "error": error,
                "attempts": attempts,
                "failed_at": datetime.now(),
                "webhook_url": settings.MAIN_BACKEND_WEBHOOK_URL,
                "reprocessed": False,
            }
        )
        logger.error(f"[DLQ] ❌ Mensagem salva na DLQ: {session_id}")
    except Exception as e:
        logger.critical(f"[DLQ] ❌❌ FALHA CRÍTICA ao salvar DLQ: {e}")


async def delayed_response_task(
    ctx, session_id: str, user_message: str, company_payload: dict
):
    try:
        logger.info(f"[WORKER] 🔄 Processando mensagem atrasada: {session_id}")

        session = await session_service.get_session(session_id)
        if not session:
            logger.warning(f"[WORKER] ⚠️ Sessão não encontrada: {session_id}")
            return

        if session.get("paused_until") and session["paused_until"] > datetime.now():
            logger.info(
                f"[WORKER] ⏸️ Pausa renovada pelo owner. Abortando resposta automática. Session: {session_id}"
            )
            return

        if session.get("last_sender_type") != "user":
            logger.info(
                f"[WORKER] 👤 Última mensagem não é do usuário. Owner assumiu controle. Abortando. Session: {session_id}"
            )
            return

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

        logger.info(f"[WORKER] 🤖 Executando grafo para {session_id}")
        graph = create_agent_graph()
        final_state = await graph.ainvoke(initial_state)

        if not final_state.get("final_response"):
            logger.error(
                f"[WORKER] ❌ Grafo não gerou resposta para {session_id}",
            )
            return

        response_obj: ChatResponse = final_state["final_response"]
        payload = response_obj.model_dump(mode="json")

        headers = {
            "X-Webhook-Token": settings.WEBHOOK_SECRET_TOKEN,
            "Content-Type": "application/json",
            "X-Session-Id": session_id,
            "X-Company-Id": company_id,
        }

        try:
            await send_webhook(
                settings.MAIN_BACKEND_WEBHOOK_URL,
                payload,
                headers,
            )
            logger.info(f"[WORKER] ✅ Webhook entregue: {session_id}")

        except RetryError as retry_error:
            logger.error(
                f"[WORKER] ❌ Falha após 3 tentativas de webhook: {session_id}"
            )

            await save_to_dlq(
                session_id=session_id,
                payload=payload,
                error=str(retry_error),
                attempts=3,
            )

        except Exception as webhook_error:
            logger.error(
                f"[WORKER] ❌ Erro inesperado no webhook: {webhook_error}",
                exc_info=True,
            )
            await save_to_dlq(
                session_id=session_id,
                payload=payload,
                error=str(webhook_error),
                attempts=1,
            )

    except Exception as e:
        logger.error(
            f"[WORKER] ❌ Erro crítico ao processar task: {e}",
            exc_info=True,
        )


class WorkerSettings:
    functions = [delayed_response_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
