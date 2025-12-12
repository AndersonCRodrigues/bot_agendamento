from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime, timedelta
from openai import OpenAIError
from bson import ObjectId
from bson.errors import InvalidId
from arq import create_pool
from arq.connections import RedisSettings

from .config import settings
from .database import mongodb
from .agent import create_agent_graph, GraphState
from .models import ChatRequest, CustomerProfile, CompanyConfig, CostInfo
from .models.knowledge import (
    KnowledgeEntryCreate,
    KnowledgeEntryUpdate,
    KnowledgeBulkCreate,
    KnowledgeListResponse,
    KnowledgeBulkResponse,
)
from .services.usage_service import usage_service
from .services.company_service import company_service
from .services.session_service import session_service
from .services.rag_service import rag_service
from .schemas import ChatSession

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Bot Agendador Multi-Nicho v2.1 (OTIMIZADO)")
    await mongodb.connect()
    app.state.redis = await create_pool(RedisSettings(host="localhost", port=6379))
    logger.info("Sistema pronto")
    yield
    logger.info("Encerrando")
    await app.state.redis.close()
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


@app.post("/chat", tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(
            f"[CHAT] Nova interacao. Sessao: {request.session_id} | "
            f"Empresa: {request.company.nome}"
        )

        session = await session_service.get_session(request.session_id)

        if (
            session
            and session.get("paused_until")
            and session["paused_until"] > datetime.now()
        ):
            logger.info(
                f"[CHAT] Sessão em pausa até {session['paused_until']}. Enfileirando."
            )

            user_message = ChatSession.create_message("user", request.cliente.mensagem)
            await session_service.append_messages(request.session_id, [user_message])
            await session_service.update_pause_state(
                request.session_id, session["paused_until"], "user"
            )

            await app.state.redis.enqueue_job(
                "delayed_response_task",
                session_id=request.session_id,
                user_message=request.cliente.mensagem,
                company_payload=request.company.model_dump(),
                _defer_until=session["paused_until"],
            )

            return JSONResponse(
                status_code=202,
                content={
                    "status": "queued",
                    "detail": "Bot em pausa, resposta agendada.",
                },
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


@app.post("/sessions/{session_id}/owner-interaction", tags=["Sessions"])
async def owner_interaction(session_id: str, message: str):
    try:
        paused_until = datetime.now() + timedelta(minutes=10)

        owner_msg = ChatSession.create_message(
            "assistant", message, metadata={"source": "owner"}
        )

        await session_service.append_messages(session_id, [owner_msg])
        await session_service.update_pause_state(
            session_id=session_id, paused_until=paused_until, last_sender_type="owner"
        )

        return {
            "status": "paused",
            "paused_until": paused_until.isoformat(),
            "detail": "Bot pausado por 10 minutos.",
        }
    except Exception as e:
        logger.error(f"Erro owner interaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


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


@app.post("/knowledge", tags=["Knowledge Base"], status_code=201)
async def create_knowledge_entry(
    company_id: str,
    entry: KnowledgeEntryCreate,
):
    try:
        if not company_id or len(company_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="company_id é obrigatório")

        entry_id = await rag_service.create_knowledge(
            company_id=company_id,
            question=entry.question,
            answer=entry.answer,
            category=entry.category,
            priority=entry.priority,
        )

        return {
            "status": "success",
            "entry_id": entry_id,
            "embedding_generated": True,
        }

    except HTTPException:
        raise
    except OpenAIError as e:
        logger.error(f"[KNOWLEDGE] Erro OpenAI: {e}", exc_info=True)
        raise HTTPException(
            status_code=503, detail="Serviço de embeddings temporariamente indisponível"
        )
    except Exception as e:
        logger.error(f"[KNOWLEDGE] Erro ao criar FAQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao criar FAQ: {str(e)}")


@app.get("/knowledge", response_model=KnowledgeListResponse, tags=["Knowledge Base"])
async def list_knowledge_entries(
    company_id: str,
    category: str = None,
    skip: int = 0,
    limit: int = 50,
):
    try:
        if not company_id or len(company_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="company_id é obrigatório")

        if limit > 100:
            raise HTTPException(status_code=400, detail="Limite máximo é 100 registros")

        result = await rag_service.list_knowledge(
            company_id=company_id,
            category=category,
            skip=skip,
            limit=limit,
        )

        return KnowledgeListResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[KNOWLEDGE] Erro ao listar FAQs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao listar FAQs: {str(e)}")


@app.put("/knowledge/{entry_id}", tags=["Knowledge Base"])
async def update_knowledge_entry(
    entry_id: str,
    company_id: str,
    entry: KnowledgeEntryUpdate,
):
    try:
        try:
            ObjectId(entry_id)
        except InvalidId:
            raise HTTPException(
                status_code=400, detail=f"entry_id inválido: {entry_id}"
            )

        if not company_id or len(company_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="company_id é obrigatório")

        updated = await rag_service.update_knowledge(
            entry_id=entry_id,
            company_id=company_id,
            question=entry.question,
            answer=entry.answer,
            category=entry.category,
            priority=entry.priority,
        )

        if not updated:
            raise HTTPException(
                status_code=404, detail=f"FAQ {entry_id} não encontrada"
            )

        regenerated = bool(entry.question or entry.answer or entry.category)

        return {
            "status": "success",
            "entry_id": entry_id,
            "embedding_regenerated": regenerated,
        }

    except HTTPException:
        raise
    except OpenAIError as e:
        logger.error(f"[KNOWLEDGE] Erro OpenAI ao regenerar embedding: {e}")
        raise HTTPException(status_code=503, detail="Erro ao regenerar embedding")
    except Exception as e:
        logger.error(f"[KNOWLEDGE] Erro ao atualizar FAQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar FAQ: {str(e)}")


@app.delete("/knowledge/{entry_id}", tags=["Knowledge Base"])
async def delete_knowledge_entry(
    entry_id: str,
    company_id: str,
):
    try:
        try:
            ObjectId(entry_id)
        except InvalidId:
            raise HTTPException(
                status_code=400, detail=f"entry_id inválido: {entry_id}"
            )

        if not company_id or len(company_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="company_id é obrigatório")

        deleted = await rag_service.delete_knowledge(
            entry_id=entry_id,
            company_id=company_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"FAQ {entry_id} não encontrada"
            )

        return {
            "status": "success",
            "entry_id": entry_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[KNOWLEDGE] Erro ao deletar FAQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao deletar FAQ: {str(e)}")


@app.post(
    "/knowledge/bulk",
    response_model=KnowledgeBulkResponse,
    tags=["Knowledge Base"],
    status_code=201,
)
async def bulk_create_knowledge(
    bulk_data: KnowledgeBulkCreate,
):
    try:
        if not bulk_data.company_id or len(bulk_data.company_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="company_id é obrigatório")

        if len(bulk_data.entries) == 0:
            raise HTTPException(
                status_code=400, detail="Lista de entries não pode ser vazia"
            )

        if len(bulk_data.entries) > 100:
            raise HTTPException(
                status_code=400, detail="Máximo de 100 FAQs por request"
            )

        entries_dict = [
            {
                "question": e.question,
                "answer": e.answer,
                "category": e.category,
                "priority": e.priority,
            }
            for e in bulk_data.entries
        ]

        ids = await rag_service.bulk_create(
            company_id=bulk_data.company_id,
            entries=entries_dict,
        )

        return KnowledgeBulkResponse(
            status="success",
            count=len(ids),
            ids=ids,
        )

    except HTTPException:
        raise
    except OpenAIError as e:
        logger.error(f"[KNOWLEDGE] Erro OpenAI no bulk create: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Erro ao gerar embeddings em lote")
    except Exception as e:
        logger.error(f"[KNOWLEDGE] Erro no bulk create: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro no bulk create: {str(e)}")


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
        session = await session_service.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=404, detail=f"Sessao {session_id} nao encontrada"
            )

        if "_id" in session:
            session["_id"] = str(session["_id"])

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SESSIONS] Erro ao buscar sessao: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao buscar sessao: {str(e)}")


@app.delete("/sessions/{session_id}", tags=["Sessions"])
async def delete_session(session_id: str):
    try:
        deleted = await session_service.delete_session(session_id)

        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"Sessao {session_id} nao encontrada"
            )

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
