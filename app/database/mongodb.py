from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging
from pymongo.errors import OperationFailure
from ..config import settings
from ..schemas import CompanyKnowledgeBase, ChatSession

logger = logging.getLogger(__name__)


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls):
        try:
            logger.info(f"Conectando ao MongoDB: {settings.MONGODB_URI}")
            cls.client = AsyncIOMotorClient(settings.MONGODB_URI)
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            await cls.client.admin.command("ping")
            logger.info("✓ Conectado ao MongoDB com sucesso")
            await cls._create_indexes()
        except Exception as e:
            logger.error(f"✗ Erro ao conectar no MongoDB: {e}")
            raise

    @classmethod
    async def safe_create_index(cls, collection, keys, **kwargs):
        try:
            await collection.create_index(keys, **kwargs)
        except OperationFailure as e:
            if "IndexOptionsConflict" in str(e):
                logger.warning(
                    f"⚠ Índice já existe com opções diferentes em {collection.name}"
                )
            else:
                raise

    @classmethod
    async def _create_indexes(cls):
        try:
            kb_collection = cls.db[CompanyKnowledgeBase.collection_name]
            for index in CompanyKnowledgeBase.get_indexes():
                await kb_collection.create_index(index)
            logger.info(
                f"✓ Índices criados para {CompanyKnowledgeBase.collection_name}"
            )
            session_collection = cls.db[ChatSession.collection_name]
            for index in ChatSession.get_indexes():
                await session_collection.create_index(index)
            ttl_config = ChatSession.get_ttl_index()
            await cls.safe_create_index(
                session_collection,
                ttl_config["keys"],
                expireAfterSeconds=ttl_config["expireAfterSeconds"],
            )
            logger.info(f"✓ Índices criados para {ChatSession.collection_name}")
            logger.warning(
                "⚠ Lembre-se de criar o vector search index manualmente no MongoDB Atlas "
                f"para a collection {CompanyKnowledgeBase.collection_name}"
            )
        except Exception as e:
            logger.error(f"Erro ao criar índices: {e}")

    @classmethod
    async def close(cls):
        if cls.client:
            cls.client.close()
            logger.info("✓ Conexão MongoDB fechada")

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        if cls.db is None:
            raise RuntimeError("MongoDB não está conectado. Chame connect() primeiro.")
        return cls.db


mongodb = MongoDB()


async def get_db() -> AsyncIOMotorDatabase:
    return mongodb.get_database()
