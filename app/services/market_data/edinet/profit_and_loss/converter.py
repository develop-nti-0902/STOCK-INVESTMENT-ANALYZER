"""EDINET 損益・キャッシュフローデータ変換層.

パーサーの出力を Pydantic モデルに変換し、DB保存用の辞書形式に変換する機能を提供します。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.schemas.market_data.edinet import EdinetProfitAndLossCreate
from app.services.core.converters.edinet_base_converter import EdinetBaseConverter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetProfitAndLossConverter(EdinetBaseConverter[EdinetProfitAndLossCreate]):
    """EDINET 損益・キャッシュフローデータ変換クラス.

    パーサーの出力（辞書）を Pydantic モデルに変換し、
    DB保存用の辞書形式に変換する機能を提供します。
    """

    def to_pydantic(
        self,
        data: Dict[str, Any],
    ) -> EdinetProfitAndLossCreate:
        """パーサーの出力辞書を Pydantic モデルに変換する.

        Args:
            data: パーサーの出力（年度別データ + メタデータを含む辞書）
                - period_end_date, operating_profit, eps など財務項目
                - doc_id, sec_code, submission_date, filer_name などメタデータ

        Returns:
            EdinetProfitAndLossCreate: Pydantic モデル
        """
        return super().to_pydantic(data)

    def _normalize_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "report_type": "annual",
            "operating_income": self.to_decimal(data.get("operating_profit"))
            or self.to_decimal(data.get("operating_income")),
            "net_sales": self.to_decimal(data.get("net_sales"))
            or self.to_decimal(data.get("sales")),
            "eps": self.to_decimal(data.get("eps")),
            "candidate_contexts": data.get("candidate_contexts"),
            "candidate_keys": data.get("candidate_keys"),
            "is_consolidated": data.get("is_consolidated"),
        }

    def _build_model(self, model_kwargs: Dict[str, Any]) -> EdinetProfitAndLossCreate:
        allowed = set(getattr(EdinetProfitAndLossCreate, "model_fields", {}).keys())
        filtered = {k: v for k, v in model_kwargs.items() if k in allowed}
        return EdinetProfitAndLossCreate(**filtered)

    def _to_saver_record(self, model: EdinetProfitAndLossCreate) -> Dict[str, Any]:
        """内部: EdinetProfitAndLossCreate -> Saver入力用辞書に変換する.

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
            "net_sales": getattr(model, "net_sales", None),
            "operating_income": model.operating_income,
            "eps": model.eps,
            "candidate_contexts": model.candidate_contexts,
            "candidate_keys": model.candidate_keys,
            "is_consolidated": model.is_consolidated,
        }

    def to_saver_records(self, models: List[EdinetProfitAndLossCreate]) -> List[Dict[str, Any]]:
        """複数の EdinetProfitAndLossCreate を Saver 用の辞書リストに変換する.

        Args:
            models: Pydantic モデルのリスト

        Returns:
            Saver が期待する辞書のリスト
        """
        # デフォルト実装は基底の `to_saver_records` を利用するため、冗長な上書きは削除しました。
        return super().to_saver_records(models)


__all__ = ["EdinetProfitAndLossConverter"]
