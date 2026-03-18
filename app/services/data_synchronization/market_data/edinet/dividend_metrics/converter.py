"""EDINET 配当メトリクス計算・変換層.

EdinetStockDividend + EdinetProfitAndLoss から
配当メトリクス（特に payout_ratio）を計算し、Pydantic モデルに変換します。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from app.models.market_data.edinet import EdinetProfitAndLoss, EdinetStockDividend
from app.schemas.market_data.edinet import EdinetDividendMetricsCreate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DividendMetricsConverter:
    """配当メトリクス計算・変換クラス.

    EdinetStockDividend と EdinetProfitAndLoss のペアから
    配当メトリクス（payout_ratio等）を計算し、保存用の Pydantic オブジェクトに変換します。
    """

    async def to_schema(
        self,
        dividend_record: EdinetStockDividend,
        profit_loss_record: Optional[EdinetProfitAndLoss],
    ) -> EdinetDividendMetricsCreate:
        """EdinetStockDividend + EdinetProfitAndLoss → Pydantic スキーマ変換.

        配当実績（調整済み優先）と EPS から payout_ratio を計算します。

        Args:
            dividend_record: 配当テーブルのレコード
            profit_loss_record: 損益計算書テーブルのレコード（None 可）

        Returns:
            EdinetDividendMetricsCreate: 計算済みメトリクス
        """
        # Step 1: dividend 実績額の決定
        # 注意: EPS は調整されていないため、payout_ratio の計算では
        # 未調整の `dividend_actual` を優先して使用する。
        # ただし未調整値が存在しない場合は `dividend_adj` を代替値として使用する。
        dividend_actual: Optional[Decimal] = None
        if dividend_record.dividend_actual is not None:
            dividend_actual = Decimal(str(dividend_record.dividend_actual))
        elif dividend_record.dividend_adj is not None:
            # 未調整値が無いため調整済み値を代替使用する（警告ログ）
            dividend_actual = Decimal(str(dividend_record.dividend_adj))
            logger.debug(
                f"dividend_actual is missing; using dividend_adj as fallback: "
                f"doc_id={dividend_record.edinet_document_id}, "
                f"period_end_date={dividend_record.period_end_date}"
            )

        # Step 2: EPS の取得 (Decimal に変換)
        eps: Optional[Decimal] = None
        if profit_loss_record and profit_loss_record.eps is not None:
            eps = Decimal(str(profit_loss_record.eps))

        # Step 3: payout_ratio 計算（eps > 0 の場合のみ）
        payout_ratio: Optional[Decimal] = None
        if dividend_actual is not None and eps is not None:
            if eps > 0:
                payout_ratio = dividend_actual / eps
            else:
                logger.debug(
                    f"EPS <= 0 のため payout_ratio は計算不可: "
                    f"doc_id={dividend_record.edinet_document_id}, "
                    f"period_end_date={dividend_record.period_end_date}"
                )

        return EdinetDividendMetricsCreate(
            edinet_document_id=dividend_record.edinet_document_id,
            period_end_date=dividend_record.period_end_date,
            fiscal_year=dividend_record.fiscal_year,
            dividend_actual=dividend_actual,
            eps=eps,
            payout_ratio=payout_ratio,
            is_consolidated=dividend_record.is_consolidated,
        )


__all__ = ["DividendMetricsConverter"]
