"""EDINET キャッシュフロー用データ変換層."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.schemas.edinet_cash_flow_statement import EdinetCashFlowStatementCreate
from app.services.core.converters.base_converter import BaseConverter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetCashFlowStatementConverter(BaseConverter[EdinetCashFlowStatementCreate]):
    """パーサー出力を Pydantic モデルおよび DB 保存用辞書に変換するクラス."""

    def to_pydantic(self, data: Dict[str, Any]) -> EdinetCashFlowStatementCreate:
        doc_id = data.get("doc_id", "")
        sec_code = data.get("sec_code", "")
        submission_date = data.get("submission_date")

        period_end = data.get("period_end")
        if not period_end:
            raise ValueError("period_end is required")

        try:
            fiscal_year = int(str(period_end).split("-")[0])
        except Exception:
            fiscal_year = None

        def to_decimal(value: Any) -> Optional[Decimal]:
            if value is None:
                return None
            try:
                return Decimal(str(value))
            except Exception:
                return None

        return EdinetCashFlowStatementCreate(
            doc_id=doc_id,
            sec_code=sec_code,
            submission_date=submission_date,  # type: ignore[arg-type]
            period_end_date=period_end,  # type: ignore[arg-type]
            fiscal_year=fiscal_year,
            report_type=data.get("report_type", "annual"),
            operating_cf=to_decimal(data.get("operating_cf")),
            candidate_contexts=data.get("candidate_contexts"),
            candidate_keys=data.get("candidate_keys"),
            is_consolidated=data.get("consolidation"),
        )

    def to_saver_records(self, models: List[EdinetCashFlowStatementCreate]) -> List[Dict[str, Any]]:
        return [self._to_saver_record(m) for m in models]

    def _to_saver_record(self, model: EdinetCashFlowStatementCreate) -> Dict[str, Any]:
        return {
            "doc_id": model.doc_id,
            "sec_code": model.sec_code,
            "submission_date": model.submission_date,
            "period_end_date": model.period_end_date,
            "fiscal_year": model.fiscal_year,
            "report_type": model.report_type,
            "operating_cf": model.operating_cf,
            "candidate_contexts": model.candidate_contexts,
            "candidate_keys": model.candidate_keys,
            "is_consolidated": model.is_consolidated,
        }

    def from_pydantic(self, model: EdinetCashFlowStatementCreate) -> Dict[str, Any]:
        return self._to_saver_record(model)

    def from_dataframe(self, df: Any, *args, **kwargs) -> List[EdinetCashFlowStatementCreate]:
        raise NotImplementedError(
            "from_dataframe is not implemented for EdinetCashFlowStatementConverter."
        )


__all__ = ["EdinetCashFlowStatementConverter"]
