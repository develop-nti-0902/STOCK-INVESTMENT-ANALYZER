"""EDINET 配当データ変換層.

パーサーの出力を Pydantic モデルに変換し、DB保存用の辞書に整形します。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.schemas.edinet_stock_dividend import EdinetStockDividendCreate
from app.services.core.converters.edinet_base_converter import EdinetBaseConverter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetStockDividendConverter(EdinetBaseConverter[EdinetStockDividendCreate]):
    """EDINET 配当データの変換クラス."""

    def to_pydantic(self, data: Dict[str, Any]) -> EdinetStockDividendCreate:
        # 共通テンプレートを利用
        return super().to_pydantic(data)

    def _normalize_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "report_type": "annual",
            "dividend_actual": self.to_decimal(data.get("dividend_actual")),
            "candidate_contexts": data.get("candidate_contexts"),
            "candidate_keys": data.get("candidate_keys"),
            "is_consolidated": data.get("is_consolidated"),
        }

    def _build_model(self, model_kwargs: Dict[str, Any]) -> EdinetStockDividendCreate:
        allowed = set(getattr(EdinetStockDividendCreate, "model_fields", {}).keys())
        filtered = {k: v for k, v in model_kwargs.items() if k in allowed}
        return EdinetStockDividendCreate(**filtered)

    # to_saver_records / _to_saver_record / from_pydantic / from_dataframe
    # は EdinetBaseConverter のデフォルト実装を利用する。


__all__ = ["EdinetStockDividendConverter"]
