"""EDINET 貸借対照表データ変換層.

パーサーの出力を Pydantic モデルに変換し、DB保存用の辞書形式に変換する機能を提供します。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.schemas.edinet_balance_sheet import EdinetBalanceSheetCreate
from app.services.core.converters.base_converter import BaseConverter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetBalanceSheetConverter(BaseConverter[EdinetBalanceSheetCreate]):
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
        # メタデータを抽出
        doc_id = data.get("doc_id", "")
        sec_code = data.get("sec_code", "")
        submission_date = data.get("submission_date")
        filer_name = data.get("filer_name")

        # 財務データを抽出
        period_end = data.get("period_end")
        if not period_end:
            raise ValueError("period_end is required")

        # fiscal_year を算出
        try:
            fiscal_year = int(str(period_end).split("-")[0])
        except Exception:
            fiscal_year = None

        # Decimal 変換用のヘルパー
        def to_decimal(value: Any) -> Optional[Decimal]:
            if value is None:
                return None
            try:
                return Decimal(str(value))
            except Exception:
                return None

        return EdinetBalanceSheetCreate(
            doc_id=doc_id,
            sec_code=sec_code,
            filer_name=filer_name,
            submission_date=submission_date,  # type: ignore[arg-type]
            period_end_date=period_end,  # type: ignore[arg-type]
            fiscal_year=fiscal_year,
            report_type="annual",
            total_assets=to_decimal(data.get("assets")),
            current_assets=None,
            non_current_assets=None,
            cash_and_equivalents=None,
            total_liabilities=to_decimal(data.get("liabilities")),
            current_liabilities=None,
            non_current_liabilities=None,
            total_equity=to_decimal(data.get("equity")),
            shareholders_equity=None,
            retained_earnings=None,
            candidate_contexts=None,
            candidate_keys=None,
            is_consolidated=data.get("consolidation"),
        )

    def to_saver_records(self, models: List[EdinetBalanceSheetCreate]) -> List[Dict[str, Any]]:
        """複数の EdinetBalanceSheetCreate を Saver 用の辞書リストに変換する.

        Args:
            models: Pydantic モデルのリスト

        Returns:
            Saver が期待する辞書のリスト
        """
        return [self._to_saver_record(m) for m in models]

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

    def from_pydantic(self, model: EdinetBalanceSheetCreate) -> Dict[str, Any]:
        """Pydantic モデルを辞書に変換する（_to_saver_record のエイリアス）.

        Args:
            model: Pydantic モデル

        Returns:
            辞書形式のデータ
        """
        return self._to_saver_record(model)

    def from_dataframe(self, df: Any, *args, **kwargs) -> List[EdinetBalanceSheetCreate]:
        """DataFrame からの変換（現在は未実装）.

        Args:
            df: データフレーム

        Raises:
            NotImplementedError: この機能は現在未実装
        """
        raise NotImplementedError(
            "from_dataframe is not implemented for EdinetBalanceSheetConverter."
        )


__all__ = ["EdinetBalanceSheetConverter"]
