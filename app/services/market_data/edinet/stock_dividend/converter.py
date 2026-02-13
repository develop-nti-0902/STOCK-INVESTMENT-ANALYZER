"""EDINET 配当データ変換層.

パーサーの出力を Pydantic モデルに変換し、DB保存用の辞書に整形します。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.schemas.edinet_stock_dividend import EdinetStockDividendCreate
from app.services.core.converters.base_converter import BaseConverter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetStockDividendConverter(BaseConverter[EdinetStockDividendCreate]):
    """EDINET 配当データの変換クラス."""

    def to_pydantic(self, data: Dict[str, Any]) -> EdinetStockDividendCreate:
        """パーサー出力を Pydantic モデルに変換する."""
        doc_id = data.get("doc_id", "")
        sec_code = data.get("sec_code", "")
        submission_date = data.get("submission_date")

        period_end_date = data.get("period_end_date")
        if not period_end_date:
            raise ValueError("period_end_date is required")

        try:
            fiscal_year = int(str(period_end_date).split("-")[0])
        except Exception:
            fiscal_year = None

        def to_decimal(value: Any) -> Optional[Decimal]:
            if value is None:
                return None
            try:
                return Decimal(str(value))
            except Exception:
                return None

        return EdinetStockDividendCreate(
            doc_id=doc_id,
            sec_code=sec_code,
            submission_date=submission_date,  # type: ignore[arg-type]
            period_end_date=period_end_date,  # type: ignore[arg-type]
            fiscal_year=fiscal_year,
            report_type="annual",
            dividend_actual=to_decimal(data.get("dividend_actual")),
            candidate_contexts=data.get("candidate_contexts"),
            candidate_keys=data.get("candidate_keys"),
            is_consolidated=data.get("is_consolidated"),
        )

    def to_saver_records(self, models: List[EdinetStockDividendCreate]) -> List[Dict[str, Any]]:
        return [self._to_saver_record(m) for m in models]

    def _to_saver_record(self, model: EdinetStockDividendCreate) -> Dict[str, Any]:
        return {
            "doc_id": model.doc_id,
            "sec_code": model.sec_code,
            "submission_date": model.submission_date,
            "period_end_date": model.period_end_date,
            "fiscal_year": model.fiscal_year,
            "report_type": model.report_type,
            "dividend_actual": model.dividend_actual,
            "candidate_contexts": model.candidate_contexts,
            "candidate_keys": model.candidate_keys,
            "is_consolidated": model.is_consolidated,
        }

    def from_pydantic(self, model: EdinetStockDividendCreate) -> Dict[str, Any]:
        return self._to_saver_record(model)

    def from_dataframe(self, df: Any, *args, **kwargs) -> List[EdinetStockDividendCreate]:
        raise NotImplementedError(
            "from_dataframe is not implemented for EdinetStockDividendConverter."
        )


__all__ = ["EdinetStockDividendConverter"]
