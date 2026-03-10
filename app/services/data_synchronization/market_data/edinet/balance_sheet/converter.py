"""EDINET 貸借対照表データ変換層.

パーサーの出力を Pydantic モデルに変換し、DB保存用の辞書形式に変換する機能を提供します。
"""

from __future__ import annotations

from typing import Any, Dict

from app.schemas.market_data.edinet import EdinetBalanceSheetCreate
from app.services.data_synchronization._core.converters.edinet_base_converter import (
    EdinetBaseConverter,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetBalanceSheetConverter(EdinetBaseConverter[EdinetBalanceSheetCreate]):
    """EDINET 貸借対照表データ変換クラス.

    パーサーの出力（辞書）を Pydantic モデルに変換し、
    DB保存用の辞書形式に変換する機能を提供します。
    """

    def to_pydantic(
        self,
        data: Dict[str, Any],
    ) -> EdinetBalanceSheetCreate:
        """パーサーの出力辞書を Pydantic モデルに変換する.

        Args:
            data: パーサーの出力（年度別データ + メタデータを含む辞書）
                - period_end_date, total_assets, net_assets など財務項目
                - doc_id, sec_code, submission_date, filer_name などメタデータ

        Returns:
            EdinetBalanceSheetCreate: Pydantic モデル
        """
        return super().to_pydantic(data)

    def _normalize_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "report_type": "annual",
            "total_assets": self.to_decimal(data.get("total_assets")),
            "net_assets": self.to_decimal(data.get("net_assets")),
            "shareholders_equity": self.to_decimal(data.get("shareholders_equity")),
            "bps": self.to_decimal(data.get("bps")),
            "equity_ratio": self.to_decimal(data.get("equity_ratio")),
            "candidate_contexts": data.get("candidate_contexts"),
            "candidate_keys": data.get("candidate_keys"),
            "is_consolidated": data.get("is_consolidated"),
        }

    def _build_model(self, model_kwargs: Dict[str, Any]) -> EdinetBalanceSheetCreate:
        allowed = set(getattr(EdinetBalanceSheetCreate, "model_fields", {}).keys())
        filtered = {k: v for k, v in model_kwargs.items() if k in allowed}
        return EdinetBalanceSheetCreate(**filtered)

    def _to_saver_record(self, model: EdinetBalanceSheetCreate) -> Dict[str, Any]:
        """内部: EdinetBalanceSheetCreate -> Saver入力用辞書に変換する.

        Args:
            model: Pydantic モデル

        Returns:
            Saver が期待するフィールドを持つ辞書
        """
        return {
            "doc_id": model.doc_id,
            "sec_code": model.sec_code,
            "submission_date": model.submission_date,
            "period_end_date": model.period_end_date,
            "fiscal_year": model.fiscal_year,
            "report_type": model.report_type,
            "total_assets": getattr(model, "total_assets", None),
            "net_assets": getattr(model, "net_assets", None),
            "shareholders_equity": getattr(model, "shareholders_equity", None),
            "bps": getattr(model, "bps", None),
            "equity_ratio": getattr(model, "equity_ratio", None),
            "candidate_contexts": model.candidate_contexts,
            "candidate_keys": model.candidate_keys,
            "is_consolidated": model.is_consolidated,
        }


__all__ = ["EdinetBalanceSheetConverter"]
