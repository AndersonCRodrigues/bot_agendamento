import logging
from datetime import datetime
from typing import Dict, List, Any
from ..database import mongodb
from ..models.usage import TokenUsageRecord

logger = logging.getLogger(__name__)


class UsageService:
    collection_name = "token_usage"

    async def track_usage(
        self,
        company_id: str,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4o",
    ):
        """Salva o registro de tokens no banco"""
        try:
            now = datetime.utcnow()
            total = input_tokens + output_tokens

            # Sem cálculo de custo, apenas registro técnico
            record = TokenUsageRecord(
                company_id=company_id,
                session_id=session_id,
                timestamp=now,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total,
                date_str=now.strftime("%Y-%m-%d"),
                month_str=now.strftime("%Y-%m"),
                year_str=now.strftime("%Y"),
            )

            db = mongodb.get_database()
            await db[self.collection_name].insert_one(record.model_dump())

            logger.debug(f"[USAGE] Tokens registrados: {total}")
            return record

        except Exception as e:
            logger.error(f"[USAGE] Erro ao salvar tokens: {e}")

    async def get_metrics(
        self, company_id: str, period: str = "daily"
    ) -> List[Dict[str, Any]]:
        """
        Gera relatório de consumo de tokens.
        Args:
            period: 'daily', 'monthly', 'yearly', 'total'
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            # Define o campo de agrupamento baseado no período
            group_field = "$date_str"  # Default daily
            if period == "monthly":
                group_field = "$month_str"
            elif period == "yearly":
                group_field = "$year_str"
            elif period == "total":
                group_field = None  # Agrupa tudo

            pipeline = [
                {"$match": {"company_id": company_id}},
                {
                    "$group": {
                        "_id": group_field,
                        "total_interactions": {"$sum": 1},
                        "total_input_tokens": {"$sum": "$input_tokens"},
                        "total_output_tokens": {"$sum": "$output_tokens"},
                        "total_tokens": {"$sum": "$total_tokens"},
                    }
                },
                {"$sort": {"_id": -1}},  # Mais recente primeiro
            ]

            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)

            # Formata retorno
            return [
                {
                    "period": r["_id"] or "TOTAL",
                    "interactions": r["total_interactions"],
                    "tokens": {
                        "input": r["total_input_tokens"],
                        "output": r["total_output_tokens"],
                        "total": r["total_tokens"],
                    },
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"[USAGE] Erro ao gerar relatório: {e}")
            return []


# Instância global
usage_service = UsageService()
