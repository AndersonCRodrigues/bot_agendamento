from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import settings
from .database import mongodb
from .agent import create_agent_graph, GraphState
from .models import ChatRequest, ChatResponse, CustomerProfile, CompanyConfig, CostInfo
from .services.usage_service import usage_service
from .services.company_service import company_service

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Bot Agendador Multi-Nicho v2 (OTIMIZADO)")
    await mongodb.connect()
    logger.info("Sistema pronto")
    yield
    logger.info("Encerrando")
    await mongodb.close()


app = FastAPI(
    title="Bot Agendador Multi-Nicho OTIMIZADO",
    description="API com bot de agendamento otimizado",
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
            f"[CHAT] Nova interação. Sessão: {request.session_id} | "
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
        )

        graph = create_agent_graph()
        final_state = await graph.ainvoke(initial_state)

        if final_state.get("error") and not final_state.get("final_response"):
            logger.error(f"[CHAT] Erro crítico: {final_state['error']}")
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
    except Exception as e:
        logger.error(f"[CHAT] Erro não tratado: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/companies/{company_id}/config", tags=["Companies"])
async def create_or_update_company_config(company_id: str, config: CompanyConfig):
    """Cria ou atualiza configuração personalizada"""
    try:
        result = await company_service.create_or_update_config(company_id, config)
        return {
            "status": "success",
            "company_id": result.company_id,
            "updated_at": result.updated_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Erro ao criar/atualizar config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/companies/{company_id}/config", tags=["Companies"])
async def get_company_config(company_id: str):
    """Recupera configuração"""
    try:
        config = await company_service.get_config(company_id)
        return {"company_id": company_id, "config": config}
    except Exception as e:
        logger.error(f"Erro ao buscar config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/companies", tags=["Companies"])
async def list_companies(skip: int = 0, limit: int = 50):
    """Lista todas as empresas"""
    try:
        result = await company_service.list_companies(skip, limit)
        return result
    except Exception as e:
        logger.error(f"Erro ao listar companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/companies/{company_id}/config", tags=["Companies"])
async def delete_company_config(company_id: str):
    """Desativa configuração"""
    try:
        deleted = await company_service.delete_config(company_id)
        if deleted:
            return {"status": "success", "company_id": company_id}
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                "Sistema otimizado: economia de ~95% em tokens de prompt "
                "através de filtragem inteligente de agenda"
            ),
        }
    except Exception as e:
        logger.error(f"Erro metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/ranking", tags=["Metrics"])
async def get_company_ranking(period: str = "monthly", limit: int = 10):
    """Ranking de empresas por consumo"""
    try:
        ranking = await usage_service.get_company_ranking(period=period, limit=limit)
        return {"period": period, "ranking": ranking}
    except Exception as e:
        logger.error(f"Erro ranking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "scheduling-bot-v2-optimized",
        "optimizations": [
            "Agenda filtrada (95% menos tokens)",
            "Extração de entidades sem LLM",
            "Cache de tools",
            "Tracking por node",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
