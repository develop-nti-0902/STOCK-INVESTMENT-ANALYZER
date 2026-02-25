"""EDINET 配当情報サービスのオーケストレーションモジュール。

このモジュールはパーサ・コンバータ・セーバ等を組み合わせた上位サービスを提供します。
"""

from __future__ import annotations

from datetime import date
from typing import Any, List

from app.models.market_data.edinet import EdinetStockDividend
from app.services.data_synchronization.market_data.edinet.download_service import (
    EdinetDownloadService,
)
from app.services.data_synchronization.market_data.edinet.file_manager import EdinetFileManager
from app.services.data_synchronization.market_data.edinet.stock_dividend.converter import (
    EdinetStockDividendConverter,
)
from app.services.data_synchronization.market_data.edinet.stock_dividend.parser import (
    EdinetStockDividendParser,
)
from app.services.data_synchronization.market_data.edinet.stock_dividend.saver import (
    EdinetStockDividendSaver,
)
from app.services.data_synchronization.market_data.edinet.update_service import (
    EdinetAggregateUpdateService,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetStockDividendService:
    """EDINET 配当情報のオーケストレーションサービス."""

    def __init__(
        self,
        parser: EdinetStockDividendParser,
        converter: EdinetStockDividendConverter,
        saver: EdinetStockDividendSaver,
        file_manager: EdinetFileManager,
        download_service: EdinetDownloadService,
    ) -> None:
        """パーサ/コンバータ/セーバ等のヘルパーでオーケストレーションサービスを初期化します。"""
        self.parser = parser
        self.converter = converter
        self.saver = saver
        self.file_manager = file_manager
        self.download_service = download_service

        parser_callable = getattr(self.parser, "parse_root", getattr(self.parser, "parse", None))
        saver_callable = getattr(self.saver, "save", getattr(self.saver, "save_single", None))
        pairs = []
        if parser_callable is not None and saver_callable is not None:
            pairs.append((parser_callable, self.converter, saver_callable))

        self._aggregate = EdinetAggregateUpdateService(
            download_service=download_service, parser_saver_pairs=pairs
        )

    async def get_latest_data(self, sec_code: str) -> Any:
        """指定した証券コードの最新配当データを返します。"""
        return await self.saver.get_latest_by_sec_code(sec_code)

    async def get_by_period(self, sec_code: str, period_end_date: date) -> Any:
        """指定の期日に該当する配当レコードを返します。"""
        return await self.saver.repository.find_by_period(sec_code, period_end_date)

    async def get_annual_data(self, sec_code: str, fiscal_year: int) -> Any:
        """指定の会計年度の配当レコードを返します。"""
        return await self.saver.repository.find_by_fiscal_year(sec_code, fiscal_year)

    async def get_multiple_latest(self, sec_codes: list[str]) -> List[EdinetStockDividend]:
        """複数の証券コードについて各銘柄の最新配当レコードを返します。"""
        return await self.saver.repository.get_latest_by_sec_codes(sec_codes)

    async def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """ダウンロード済みの古いファイルを削除し、削除数を返します。"""
        work_dir = getattr(self.download_service, "work_dir", None)
        if work_dir is None:
            return 0
        return self.file_manager.cleanup_old_files(work_dir, max_age_hours=max_age_hours)

    async def adjust_dividends_by_splits(self) -> int:
        """`stock_split` を参照して `dividend_adj` を計算・保存します。

        処理概要:
            1. 初めに、すべての配当レコードに対して `dividend_adj` が未設定の場合は `dividend_actual` で初期化します。
            2. その後、`stock_split` に登録されている各銘柄について、分割履歴を参照して補正係数を算出し、
               `dividend_adj` を更新します。

        戻り値: 更新・初期化したレコード数を返します。
        """

        from decimal import Decimal

        from sqlalchemy import select

        from app.models.market_data.edinet.stock_split import StockSplit
        from app.utils.stock_code_converter import to_edinet_code

        session = getattr(self.saver, "session", None)
        if session is None:
            raise RuntimeError("No DB session available on saver")

        # ステップ 1: すべての配当レコードに dividend_adj を初期化
        all_divs_res = await session.execute(select(EdinetStockDividend))
        all_divs = all_divs_res.scalars().all()

        initialized = 0
        for div in all_divs:
            if div.dividend_actual is None:
                continue
            if div.dividend_adj is None:
                div.dividend_adj = Decimal(str(div.dividend_actual)).quantize(Decimal("0.01"))
                initialized += 1

        # 初期化した変更をコミット
        if initialized:
            await session.commit()
            logger.info("Initialized %s dividend_adj records with dividend_actual", initialized)

        # ステップ 2: `stock_split` から銘柄コードの一覧を取得（stock_master 形式）
        codes_res = await session.execute(select(StockSplit.code).distinct())
        codes_raw = [row[0] for row in codes_res.fetchall()]

        adjusted = 0
        for orig_code in codes_raw:
            # stock_master 形式のコードを EDINET 形式に変換
            try:
                edinet_code = to_edinet_code(orig_code)
            except Exception:
                logger.exception("Failed to convert code %s to EDINET format", orig_code)
                continue

            # 指定銘柄の分割履歴を発効日順に取得（orig_code=stock_master 形式で照合）
            splits_res = await session.execute(
                select(StockSplit)
                .where(StockSplit.code == orig_code)
                .order_by(StockSplit.effective_date)
            )
            splits = splits_res.scalars().all()

            if not splits:
                continue

            # 当該銘柄の配当レコードを全件取得（EDINET 形式で照合）
            divs_res = await session.execute(
                select(EdinetStockDividend).where(EdinetStockDividend.sec_code == edinet_code)
            )
            divs = divs_res.scalars().all()

            for div in divs:
                if div.dividend_actual is None:
                    continue

                # 補正係数を算出（record.period_end_date より後の分割について ratio_from/ratio_to を乗算）
                multiplier = Decimal(1)
                for sp in splits:
                    if sp.effective_date > div.period_end_date:
                        if sp.ratio_from is None or sp.ratio_to is None or sp.ratio_to == 0:
                            continue
                        multiplier *= Decimal(sp.ratio_from) / Decimal(sp.ratio_to)

                # 補正係数が 1 でなければ調整後配当を設定
                if multiplier != Decimal(1):
                    try:
                        # 必要に応じて Decimal に変換
                        actual = Decimal(str(div.dividend_actual))
                    except Exception:
                        continue

                    adj = (actual * multiplier).quantize(Decimal("0.01"))
                    div.dividend_adj = adj
                    adjusted += 1

        # 補正後の変更をコミット
        if adjusted:
            await session.commit()
            logger.info("Adjusted %s dividend records by stock splits", adjusted)

        total_updated = initialized + adjusted
        logger.info("Total %s dividend records updated/initialized", total_updated)
        return total_updated


__all__ = ["EdinetStockDividendService"]
