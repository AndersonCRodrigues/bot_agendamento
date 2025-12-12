from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from openai import OpenAIError

from .config import settings
from .database import mongodb
from .agent import create_agent_graph, GraphState
from .models import ChatRequest, ChatResponse, CustomerProfile, CompanyConfig, CostInfo
from .services.usage_service import usage_service
from .services.company_service import company_service
from .services.session_service import session_service

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Bot Agendador Multi-Nicho v2.1 (OTIMIZADO)")
    await mongodb.connect()
    logger.info("Sistema pronto")
    yield
    logger.info("Encerrando")
    await mongodb.close()


app = FastAPI(
    title="Bot Agendador Multi-Nicho OTIMIZADO",
    description="API com bot de agendamento otimizado para multiplos nichos",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(
            f"[CHAT] Nova interacao. Sessao: {request.session_id} | "
            f"Empresa: {request.company.nome}"
        )

        if request.company.config_override:
            company_config = request.company.config_override.model_dump()
        else:
            config_obj = await company_service.get_config(request.company.id)
            company_config = config_obj.model_dump()

        customer_profile = CustomerProfile(
            telefone=request.cliente.telefone,
            nome=request.cliente.nome,
            email=request.cliente.email,
        )

        initial_state = GraphState(
            company_id=request.company.id,
            session_id=request.session_id,
            user_message=request.cliente.mensagem,
            company_config=company_config,
            customer_profile=customer_profile.model_dump(),
            company_agenda=request.company.agenda,
            full_agenda=None,
            filtered_agenda=None,
            chat_history=[],
            recent_history=[],
            sentiment_result=None,
            intent_result=None,
            sentiment_analyzed=False,
            intent_analyzed=False,
            tools_validated=False,
            is_data_complete=False,
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

        if final_state.get("error") and not final_state.get("final_response"):
            logger.error(f"[CHAT] Erro critico: {final_state['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro no processamento: {final_state['error']}",
            )

        response = final_state["final_response"]

        total_tokens = final_state.get("prompt_tokens", 0) + final_state.get(
            "completion_tokens", 0
        )

        response.cost_info = CostInfo(
            total_tokens=total_tokens,
            input_tokens=final_state.get("prompt_tokens", 0),
            output_tokens=final_state.get("completion_tokens", 0),
        )

        logger.info(
            f"[CHAT] Sucesso. Tokens: {total_tokens} | "
            f"Diretiva: {response.directives.type}"
        )

        return response

    except HTTPException:
        raise
    except OpenAIError as e:
        logger.error(f"[CHAT] Erro OpenAI: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de IA temporariamente indisponivel",
        )
    except Exception as e:
        logger.error(f"[CHAT] Erro nao tratado: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@app.post("/companies/{company_id}/config", tags=["Companies"])
async def create_or_update_company_config(company_id: str, config: CompanyConfig):
    try:
        result = await company_service.create_or_update_config(company_id, config)
        return {
            "status": "success",
            "company_id": result.company_id,
            "updated_at": result.updated_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Erro ao criar/atualizar config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao processar configuracao")


@app.get("/companies/{company_id}/config", tags=["Companies"])
async def get_company_config(company_id: str):
    try:
        config = await company_service.get_config(company_id)
        return {"company_id": company_id, "config": config}
    except Exception as e:
        logger.error(f"Erro ao buscar config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar configuracao")


@app.get("/companies", tags=["Companies"])
async def list_companies(skip: int = 0, limit: int = 50):
    try:
        result = await company_service.list_companies(skip, limit)
        return result
    except Exception as e:
        logger.error(f"Erro ao listar companies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao listar empresas")


@app.delete("/companies/{company_id}/config", tags=["Companies"])
async def delete_company_config(company_id: str):
    try:
        deleted = await company_service.delete_config(company_id)
        if deleted:
            return {"status": "success", "company_id": company_id}
        raise HTTPException(status_code=404, detail="Empresa nao encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao deletar configuracao")


@app.get("/metrics/usage", tags=["Metrics"])
async def get_usage_metrics(
    company_id: str = None,
    period: str = "daily",
    start_date: str = None,
    end_date: str = None,
):
    try:
        metrics = await usage_service.get_metrics(
            company_id=company_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
        return {
            "company_id": company_id or "all",
            "period": period,
            "filters": {"start_date": start_date, "end_date": end_date},
            "data": metrics,
            "optimization_note": (
                "Sistema otimizado: economia de 95% em tokens de prompt "
                "atraves de filtragem inteligente de agenda"
            ),
        }
    except Exception as e:
        logger.error(f"Erro metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar metricas")


@app.get("/metrics/ranking", tags=["Metrics"])
async def get_company_ranking(period: str = "monthly", limit: int = 10):
    try:
        ranking = await usage_service.get_company_ranking(period=period, limit=limit)
        return {"period": period, "ranking": ranking}
    except Exception as e:
        logger.error(f"Erro ranking: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar ranking")


@app.get("/sessions/{session_id}", tags=["Sessions"])
async def get_session(session_id: str):
    try:
        logger.info(f"[SESSIONS] Buscando sessao: {session_id}")

        session = await session_service.get_session(session_id)

        if not session:
            logger.warning(f"[SESSIONS] Sessao nao encontrada: {session_id}")
            raise HTTPException(
                status_code=404, detail=f"Sessao {session_id} nao encontrada"
            )

        from bson import ObjectId

        if "_id" in session:
            session["_id"] = str(session["_id"])

        logger.info(f"[SESSIONS] Sessao encontrada: {session_id}")
        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SESSIONS] Erro ao buscar sessao: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao buscar sessao: {str(e)}")


@app.delete("/sessions/{session_id}", tags=["Sessions"])
async def delete_session(session_id: str):
    try:
        logger.info(f"[SESSIONS] Deletando sessao: {session_id}")

        deleted = await session_service.delete_session(session_id)

        if not deleted:
            logger.warning(
                f"[SESSIONS] Sessao nao encontrada para deletar: {session_id}"
            )
            raise HTTPException(
                status_code=404, detail=f"Sessao {session_id} nao encontrada"
            )

        logger.info(f"[SESSIONS] Sessao deletada com sucesso: {session_id}")
        return {"status": "success", "session_id": session_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SESSIONS] Erro ao deletar sessao: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao deletar sessao: {str(e)}")


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "scheduling-bot-v2-optimized",
        "version": "2.1.0",
    }


@app.get("/health/ready", tags=["System"])
async def readiness_check():
    checks = {"mongodb": False, "openai": False}

    try:
        db = mongodb.get_database()
        await db.command("ping")
        checks["mongodb"] = True
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")

    try:
        from .services.openai_service import openai_service

        test_embedding = await openai_service.get_embedding("test")
        if len(test_embedding) > 0:
            checks["openai"] = True
    except Exception as e:
        logger.error(f"OpenAI health check failed: {e}")

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
    }, status_code


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
