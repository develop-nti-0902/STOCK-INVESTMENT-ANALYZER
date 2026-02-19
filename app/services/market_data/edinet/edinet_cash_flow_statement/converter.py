"""EDINET キャッシュフロー用データ変換層."""

from __future__ import annotations

from typing import Any, Dict

from app.schemas.market_data.edinet import EdinetCashFlowStatementCreate
from app.services.core.converters.edinet_base_converter import EdinetBaseConverter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetCashFlowStatementConverter(EdinetBaseConverter[EdinetCashFlowStatementCreate]):
    """パーサー出力を Pydantic モデルおよび DB 保存用辞書に変換するクラス."""

    def to_pydantic(self, data: Dict[str, Any]) -> EdinetCashFlowStatementCreate:
        """パーサー出力辞書を Pydantic モデル `EdinetCashFlowStatementCreate` に変換して返します."""
        return super().to_pydantic(data)

    def _normalize_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "report_type": data.get("report_type", "annual"),
            "operating_cf": self.to_decimal(data.get("operating_cf")),
            "candidate_contexts": data.get("candidate_contexts"),
            "candidate_keys": data.get("candidate_keys"),
            "is_consolidated": data.get("consolidation"),
        }

    def _build_model(self, model_kwargs: Dict[str, Any]) -> EdinetCashFlowStatementCreate:
        allowed = set(getattr(EdinetCashFlowStatementCreate, "model_fields", {}).keys())
        filtered = {k: v for k, v in model_kwargs.items() if k in allowed}
        return EdinetCashFlowStatementCreate(**filtered)

    # use EdinetBaseConverter defaults for saver/from_pydantic/from_dataframe


__all__ = ["EdinetCashFlowStatementConverter"]
