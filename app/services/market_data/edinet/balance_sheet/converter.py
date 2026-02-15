"""EDINET 貸借対照表データ変換層.

パーサーの出力を Pydantic モデルに変換し、DB保存用の辞書形式に変換する機能を提供します。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.schemas.edinet_balance_sheet import EdinetBalanceSheetCreate
from app.services.core.converters.edinet_base_converter import EdinetBaseConverter
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
                - period_end, assets, liabilities など財務項目
                - doc_id, sec_code, submission_date, filer_name などメタデータ

        Returns:
            EdinetBalanceSheetCreate: Pydantic モデル
        """
        # サブクラスは _normalize_fields と _build_model を実装
        # ここではそれらを利用してモデルを構築する。
        # 処理の詳細は EdinetBaseConverter.to_pydantic に委任されるため
        # サブクラス側で _normalize_fields/_build_model を実装してください。
        return super().to_pydantic(data)

    def _normalize_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # 財務フィールドを Decimal に変換し、Pydantic キー名に合わせて返す
        return {
            "report_type": "annual",
            "filer_name": data.get("filer_name"),
            "total_assets": self.to_decimal(data.get("assets")),
            "current_assets": None,
            "non_current_assets": None,
            "cash_and_equivalents": None,
            "total_liabilities": self.to_decimal(data.get("liabilities")),
            "current_liabilities": None,
            "non_current_liabilities": None,
            "total_equity": self.to_decimal(data.get("equity")),
            "shareholders_equity": None,
            "retained_earnings": None,
            "candidate_contexts": None,
            "candidate_keys": None,
            "is_consolidated": data.get("consolidation"),
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
            "filer_name": model.filer_name,
            "submission_date": model.submission_date,
            "period_end_date": model.period_end_date,
            "fiscal_year": model.fiscal_year,
            "report_type": model.report_type,
            "total_assets": model.total_assets,
            "current_assets": model.current_assets,
            "non_current_assets": model.non_current_assets,
            "cash_and_equivalents": model.cash_and_equivalents,
            "total_liabilities": model.total_liabilities,
            "current_liabilities": model.current_liabilities,
            "non_current_liabilities": model.non_current_liabilities,
            "total_equity": model.total_equity,
            "shareholders_equity": model.shareholders_equity,
            "retained_earnings": model.retained_earnings,
            "candidate_contexts": model.candidate_contexts,
            "candidate_keys": model.candidate_keys,
            "is_consolidated": model.is_consolidated,
        }


__all__ = ["EdinetBalanceSheetConverter"]
