import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
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
        node_name: Optional[str] = None,
    ):
        """Registra consumo de tokens"""
        try:
            now = datetime.now()
            total = input_tokens + output_tokens

            record = TokenUsageRecord(
                company_id=company_id,
                session_id=session_id,
                timestamp=now,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total,
                node_name=node_name,
                date_str=now.strftime("%Y-%m-%d"),
                month_str=now.strftime("%Y-%m"),
                year_str=now.strftime("%Y"),
                week_str=now.strftime("%Y-W%U"),
            )

            db = mongodb.get_database()
            await db[self.collection_name].insert_one(record.model_dump())

            logger.debug(f"[USAGE] Tokens registrados: {total} (node: {node_name})")
            return record

        except Exception as e:
            logger.error(f"[USAGE] Erro ao salvar tokens: {e}")

    async def get_metrics(
        self,
        company_id: Optional[str] = None,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Gera relatório de consumo de tokens.
        Args:
            company_id: ID da empresa (None para todas)
            period: 'daily', 'weekly', 'monthly', 'yearly', 'total'
            start_date: Data inicial (YYYY-MM-DD)
            end_date: Data final (YYYY-MM-DD)
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            match_stage = {}
            if company_id:
                match_stage["company_id"] = company_id

            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                if date_filter:
                    match_stage["date_str"] = date_filter

            group_field_map = {
                "daily": "$date_str",
                "weekly": "$week_str",
                "monthly": "$month_str",
                "yearly": "$year_str",
                "total": None,
            }

            group_field = group_field_map.get(period, "$date_str")

            group_stage = {
                "_id": group_field,
                "total_interactions": {"$sum": 1},
                "total_input_tokens": {"$sum": "$input_tokens"},
                "total_output_tokens": {"$sum": "$output_tokens"},
                "total_tokens": {"$sum": "$total_tokens"},
                "unique_sessions": {"$addToSet": "$session_id"},
            }

            if not company_id:
                group_stage["companies"] = {"$addToSet": "$company_id"}

            pipeline = [
                {"$match": match_stage} if match_stage else {"$match": {}},
                {"$group": group_stage},
                {"$sort": {"_id": -1}},
            ]

            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)

            formatted_results = []
            for r in results:
                result_dict = {
                    "period": r["_id"] or "TOTAL",
                    "interactions": r["total_interactions"],
                    "unique_sessions": len(r["unique_sessions"]),
                    "tokens": {
                        "input": r["total_input_tokens"],
                        "output": r["total_output_tokens"],
                        "total": r["total_tokens"],
                    },
                }

                if not company_id and "companies" in r:
                    result_dict["unique_companies"] = len(r["companies"])

                formatted_results.append(result_dict)

            return formatted_results

        except Exception as e:
            logger.error(f"[USAGE] Erro ao gerar relatório: {e}")
            return []

    async def get_company_ranking(
        self, period: str = "monthly", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retorna ranking de empresas por consumo de tokens"""
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            pipeline = [
                {
                    "$group": {
                        "_id": "$company_id",
                        "total_tokens": {"$sum": "$total_tokens"},
                        "total_interactions": {"$sum": 1},
                        "unique_sessions": {"$addToSet": "$session_id"},
                    }
                },
                {"$sort": {"total_tokens": -1}},
                {"$limit": limit},
            ]

            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)

            return [
                {
                    "company_id": r["_id"],
                    "total_tokens": r["total_tokens"],
                    "total_interactions": r["total_interactions"],
                    "unique_sessions": len(r["unique_sessions"]),
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"[USAGE] Erro no ranking: {e}")
            return []


usage_service = UsageService()
