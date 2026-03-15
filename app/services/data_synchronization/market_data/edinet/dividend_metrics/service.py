"""EDINET 配当メトリクス集計・保存サービス.

EDINET_STOCK_DIVIDEND と EDINET_PROFIT_AND_LOSS から
配当メトリクスを計算・保存します。
"""

from __future__ import annotations

from app.models.market_data.edinet import EdinetStockDividend
from app.repositories.market_data.edinet import (
    EdinetDividendMetricsRepository,
    EdinetProfitAndLossRepository,
    EdinetStockDividendRepository,
)
from app.utils.logger import get_logger

from .converter import DividendMetricsConverter
from .saver import DividendMetricsSaver

logger = get_logger(__name__)


class DividendMetricsService:
    """配当メトリクス集計・保存サービス.

    EDINET_STOCK_DIVIDEND と EDINET_PROFIT_AND_LOSS から
    配当メトリクスを計算・保存します。

    Attributes:
        converter: 配当メトリクス計算・変換クラス
        saver: 配当メトリクス保存クラス
        dividend_repo: 配当テーブルリポジトリ
        profit_loss_repo: 損益計算書テーブルリポジトリ
        metrics_repo: 配当メトリクスリポジトリ
    """

    def __init__(
        self,
        converter: DividendMetricsConverter,
        saver: DividendMetricsSaver,
        dividend_repo: EdinetStockDividendRepository,
        profit_loss_repo: EdinetProfitAndLossRepository,
        metrics_repo: EdinetDividendMetricsRepository,
    ) -> None:
        """初期化.

        Args:
            converter: 配当メトリクス変換クラス
            saver: 配当メトリクス保存クラス
            dividend_repo: 配当テーブルリポジトリ
            profit_loss_repo: 損益計算書テーブルリポジトリ
            metrics_repo: 配当メトリクスリポジトリ
        """
        self.converter = converter
        self.saver = saver
        self.dividend_repo = dividend_repo
        self.profit_loss_repo = profit_loss_repo
        self.metrics_repo = metrics_repo

    async def compute_and_save_metrics(
        self,
        sec_code: str,
        dividend_records: list[EdinetStockDividend],
    ) -> dict:
        """配当レコードのリストからメトリクスを計算・保存.

        与えられた配当レコードリスト（特定の証券コード） に対して、
        対応する損益計算書レコードを検索し、配当メトリクスを計算・保存します。

        Args:
            sec_code: 証券コード
            dividend_records: 計算対象の配当レコードリスト

        Returns:
            {
                "total_records": 計算対象のレコード数,
                "matched_pairs": マッチングに成功したペア数,
                "unmatched_count": マッチング失敗数,
                "saved_records": DB に保存されたレコード数,
            }
        """
        logger.info(
            f"DividendMetricsService compute_and_save_metrics 開始: "
            f"sec_code={sec_code}, {len(dividend_records)} レコード"
        )

        # Step 1: 各 dividend レコード対応の profit_loss を検索 → メトリクス計算
        metrics_to_save = []
        matched_count = 0
        unmatched_count = 0

        for dividend_rec in dividend_records:
            # 期末日で profit_and_loss マッチング
            profit_loss_rec = await self.profit_loss_repo.find_by_period(
                sec_code,
                dividend_rec.period_end_date,
            )

            if profit_loss_rec:
                # Converter で計算
                metric_schema = await self.converter.to_schema(
                    dividend_rec,
                    profit_loss_rec,
                )
                metrics_to_save.append(metric_schema)
                matched_count += 1
            else:
                unmatched_count += 1
                logger.warning(
                    f"DividendMetricsService: P&L マッチング失敗 "
                    f"sec_code={sec_code}, period_end_date={dividend_rec.period_end_date}"
                )

        logger.info(
            f"DividendMetricsService: マッチング完了 - "
            f"成功={matched_count}, 失敗={unmatched_count}"
        )

        # Step 2: 計算結果を DB に保存
        saved_records = 0
        if metrics_to_save:
            result = await self.saver.save_many(metrics_to_save)
            saved_records = len(result)
            logger.info(f"DividendMetricsService: {saved_records} レコードを保存完了")
        else:
            logger.warning("DividendMetricsService: 計算対象レコードなし")

        return {
            "total_records": len(dividend_records),
            "matched_pairs": matched_count,
            "unmatched_count": unmatched_count,
            "saved_records": saved_records,
        }


__all__ = ["DividendMetricsService"]
