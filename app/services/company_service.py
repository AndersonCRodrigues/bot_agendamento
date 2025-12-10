import logging
from typing import Optional
from datetime import datetime
from ..database import mongodb
from ..models.company import CompanyConfig, CompanyConfigDB

logger = logging.getLogger(__name__)


class CompanyService:
    collection_name = "companies"

    async def create_or_update_config(
        self, company_id: str, config: CompanyConfig
    ) -> CompanyConfigDB:
        """Cria ou atualiza configuração de uma empresa"""
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            existing = await collection.find_one({"company_id": company_id})

            now = datetime.now()

            if existing:
                await collection.update_one(
                    {"company_id": company_id},
                    {"$set": {"config": config.model_dump(), "updated_at": now}},
                )
                logger.info(f"Configuração atualizada para {company_id}")

            else:
                config_db = CompanyConfigDB(
                    company_id=company_id, config=config, created_at=now, updated_at=now
                )
                await collection.insert_one(config_db.model_dump())
                logger.info(f"Configuração criada para {company_id}")

            updated_doc = await collection.find_one({"company_id": company_id})
            return CompanyConfigDB(**updated_doc)

        except Exception as e:
            logger.error(f"Erro ao criar/atualizar config: {e}")
            raise

    async def get_config(self, company_id: str) -> Optional[CompanyConfig]:
        """Recupera configuração de uma empresa"""
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            doc = await collection.find_one(
                {"company_id": company_id, "is_active": True}
            )

            if doc:
                return CompanyConfig(**doc["config"])

            logger.warning(f"Config não encontrada para {company_id}, usando default")
            return CompanyConfig()

        except Exception as e:
            logger.error(f"Erro ao buscar config: {e}")
            return CompanyConfig()

    async def delete_config(self, company_id: str) -> bool:
        """Soft delete de configuração"""
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            result = await collection.update_one(
                {"company_id": company_id},
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
            )

            if result.matched_count > 0:
                logger.info(f"Configuração desativada: {company_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Erro ao deletar config: {e}")
            return False

    async def list_companies(self, skip: int = 0, limit: int = 50) -> dict:
        """Lista todas as empresas configuradas"""
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            total = await collection.count_documents({"is_active": True})

            cursor = (
                collection.find(
                    {"is_active": True}, {"config.vocabularios_especificos": 0}
                )
                .skip(skip)
                .limit(limit)
                .sort("created_at", -1)
            )

            companies = await cursor.to_list(length=limit)

            return {
                "total": total,
                "companies": [
                    {
                        "company_id": c["company_id"],
                        "nome_bot": c["config"]["nome_bot"],
                        "nicho_mercado": c["config"]["nicho_mercado"],
                        "created_at": c["created_at"].isoformat(),
                        "updated_at": c["updated_at"].isoformat(),
                    }
                    for c in companies
                ],
            }

        except Exception as e:
            logger.error(f"Erro ao listar companies: {e}")
            return {"total": 0, "companies": []}


company_service = CompanyService()
