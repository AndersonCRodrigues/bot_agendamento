from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import settings
from .database import mongodb
from .agent import create_agent_graph, GraphState
from .models import ChatRequest, ChatResponse, CustomerProfile, CompanyConfig, CostInfo
from .services.usage_service import usage_service

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando Bot Agendador...")
    await mongodb.connect()
    logger.info("✅ Sistema pronto para receber agendamentos!")
    yield
    logger.info("🛑 Encerrando aplicação...")
    await mongodb.close()


app = FastAPI(
    title="Bot Agendador Multi-Nicho",
    description="API de Agendamento Inteligente com Diretivas Zero-Write",
    version="2.0.0",
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
            f"[CHAT] Nova interação. Sessão: {request.session_id} | Empresa: {request.company.nome}"
        )

        # 1. Prepara Configuração (Persona)
        # Se vier no payload (override), usa. Senão, usa Default (ou buscaria no banco)
        if request.company.config_override:
            company_config = request.company.config_override.model_dump()
        else:
            # Em produção, aqui buscaríamos no MongoDB: db.companies.find_one(...)
            # Por enquanto, usamos defaults do modelo
            company_config = CompanyConfig(
                nome_bot=f"Assistente {request.company.nome}"
            ).model_dump()

        # 2. Prepara Perfil do Cliente
        customer_profile = CustomerProfile(
            telefone=request.cliente.telefone,
            nome=request.cliente.nome,
            email=request.cliente.email,
        )

        # 3. Estado Inicial do Grafo
        initial_state = GraphState(
            # Identificadores
            company_id=request.company.id,
            session_id=request.session_id,
            user_message=request.cliente.mensagem,
            start_chat=None,  # Lógica de start chat removida ou nula por padrão
            # Objetos Ricos
            company_config=company_config,
            customer_profile=customer_profile,
            company_agenda=[
                p.model_dump() for p in request.company.equipe
            ],  # A Agenda Bruta
            # Estado Vazio
            chat_history=[],
            recent_history=[],  # Será populado pelo load_context se existir sessão anterior
            rag_knowledge=[],
            rag_formatted="",
            sentiment_result=None,
            intent_result=None,
            # Flags
            sentiment_analyzed=False,
            intent_analyzed=False,
            tools_validated=False,
            is_data_complete=False,  # Será calculado no check_integrity
            # Saída
            final_response=None,
            # Metadata
            tools_called=[],
            prompt_tokens=0,
            completion_tokens=0,
            error=None,
        )

        # 4. Executa o Grafo
        graph = create_agent_graph()
        final_state = await graph.ainvoke(initial_state)

        # 5. Tratamento de Erros
        if final_state.get("error") and not final_state.get("final_response"):
            logger.error(f"[CHAT] Erro crítico no fluxo: {final_state['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro no processamento do bot: {final_state['error']}",
            )

        # 6. Retorna Resposta
        response = final_state["final_response"]

        # Popula info de custo na resposta
        response.cost_info = CostInfo(
            total_tokens=final_state.get("prompt_tokens", 0)
            + final_state.get("completion_tokens", 0),
            input_tokens=final_state.get("prompt_tokens", 0),
            output_tokens=final_state.get("completion_tokens", 0),
        )

        logger.info(f"[CHAT] ✅ Sucesso. Diretiva: {response.directives.type}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAT] Erro não tratado: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/metrics/{company_id}/usage", tags=["Metrics"])
async def get_usage_metrics(company_id: str, period: str = "daily"):
    """
    Retorna consumo de tokens.
    Period: 'daily', 'monthly', 'yearly', 'total'
    """
    try:
        metrics = await usage_service.get_metrics(company_id, period)
        return {"company_id": company_id, "period": period, "data": metrics}
    except Exception as e:
        logger.error(f"Erro metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "scheduling-bot-v2"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
