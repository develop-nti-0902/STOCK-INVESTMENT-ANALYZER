"""EDINET 損益・キャッシュフローデータ変換層.

パーサーの出力を Pydantic モデルに変換し、DB保存用の辞書形式に変換する機能を提供します。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.schemas.edinet_profit_and_loss import EdinetProfitAndLossCreate
from app.services.core.converters.base_converter import BaseConverter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetProfitAndLossConverter(BaseConverter[EdinetProfitAndLossCreate]):
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
        # メタデータを抽出
        doc_id = data.get("doc_id", "")
        sec_code = data.get("sec_code", "")
        submission_date = data.get("submission_date")

        # 財務データを抽出
        period_end_date = data.get("period_end_date")
        if not period_end_date:
            raise ValueError("period_end_date is required")

        # fiscal_year を算出
        try:
            fiscal_year = int(str(period_end_date).split("-")[0])
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

        return EdinetProfitAndLossCreate(
            doc_id=doc_id,
            sec_code=sec_code,
            submission_date=submission_date,  # type: ignore[arg-type]
            period_end_date=period_end_date,  # type: ignore[arg-type]
            fiscal_year=fiscal_year,
            report_type="annual",
            # Map legacy input `operating_profit` to new `operating_income` field
            operating_income=to_decimal(data.get("operating_profit"))
            or to_decimal(data.get("operating_income")),
            # Map net sales if present
            net_sales=to_decimal(data.get("net_sales")) or to_decimal(data.get("sales")),
            eps=to_decimal(data.get("eps")),
            candidate_contexts=data.get("candidate_contexts"),
            candidate_keys=data.get("candidate_keys"),
            is_consolidated=data.get("is_consolidated"),
        )

    def to_saver_records(self, models: List[EdinetProfitAndLossCreate]) -> List[Dict[str, Any]]:
        """複数の EdinetProfitAndLossCreate を Saver 用の辞書リストに変換する.

        Args:
            models: Pydantic モデルのリスト

        Returns:
            Saver が期待する辞書のリスト
        """
        return [self._to_saver_record(m) for m in models]

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

    def from_pydantic(self, model: EdinetProfitAndLossCreate) -> Dict[str, Any]:
        """Pydantic モデルを辞書に変換する（_to_saver_record のエイリアス）.

        Args:
            model: Pydantic モデル

        Returns:
            辞書形式のデータ
        """
        return self._to_saver_record(model)

    def from_dataframe(self, df: Any, *args, **kwargs) -> List[EdinetProfitAndLossCreate]:
        """DataFrame からの変換（現在は未実装）.

        Args:
            df: データフレーム

        Raises:
            NotImplementedError: この機能は現在未実装
        """
        raise NotImplementedError(
            "from_dataframe is not implemented for EdinetProfitAndLossConverter."
        )


__all__ = ["EdinetProfitAndLossConverter"]
