"""新しいスクリーニングサービス - Strategyパターン対応版。

業種別スクリーニングルールをサポートする新しいサービス実装です。
"""

from __future__ import annotations

import inspect
import logging
from datetime import date
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.market_data.edinet.edinet_cash_flow_statement import EdinetCashFlowStatement
from app.models.market_data.edinet.edinet_profit_and_loss import EdinetProfitAndLoss
from app.models.market_data.edinet.edinet_stock_dividend import EdinetStockDividend
from app.repositories.market_data.stock_master import (
    StockCodeMappingRepository,
    StockMasterRepository,
)
from app.repositories.screening.screening_result_repository import ScreeningResultRepository
from app.services.data_synchronization.market_data.stock_master.service import StockMasterService
from app.services.screening.models import ScreeningResult
from app.services.screening.strategy_factory import ScreeningStrategyFactory

logger = logging.getLogger(__name__)


class ScreeningService:
    """Strategyパターンを用いた新しいスクリーニングサービス。

    業種別のスクリーニングルールをサポートします。
    """

    def __init__(
        self,
        financial_query_service: Any,
        stock_master_maker: Optional[async_sessionmaker[AsyncSession]] = None,
        screening_result_maker: Optional[async_sessionmaker[AsyncSession]] = None,
        screening_result_factory: Callable[
            [AsyncSession], ScreeningResultRepository
        ] = ScreeningResultRepository,
    ):
        """初期化。

        Args:
            financial_query_service: 財務データ取得サービス
            stock_master_maker: 銘柄マスター用のセッションメーカー
            screening_result_maker: スクリーニング結果用のセッションメーカー
            screening_result_factory: ScreeningResultRepository ファクトリ
        """
        self._fq = financial_query_service
        self._stock_master_maker = stock_master_maker
        self._screening_result_maker = screening_result_maker
        self._screening_result_factory = screening_result_factory
        self._strategy_factory = ScreeningStrategyFactory()

    async def _async_fetch_all_stock_master_codes(self) -> List[str]:
        """銘柄マスターから全銘柄を取得。"""
        maker = self._stock_master_maker
        if maker is None:
            raise RuntimeError("stock_master_maker is required to fetch all codes")
        try:
            async with maker() as session:
                repo = StockMasterRepository(session=session)
                sm_service = StockMasterService(repo=repo)
                symbols = await sm_service.get_all_active_symbols()
                out: List[str] = []
                mapping_repo = StockCodeMappingRepository(session=session)
                for c in symbols:
                    try:
                        mapping = await mapping_repo.get_by_stock_code(c)
                        if mapping:
                            out.append(mapping.sec_code)
                    except Exception as e:
                        logger.debug("failed to get mapping for code %s: %s", c, e)
                return out
        except Exception as exc:
            logger.error("fetch stock master failed: %s", exc)
            return []

    async def _async_fetch_sec_codes_with_edinet_data(self) -> List[str]:
        """EDINETデータが存在する銘柄コードを取得。"""
        if self._stock_master_maker is None:
            # EDINETデータがない場合は全銘柄を扱う
            return await self._async_fetch_all_stock_master_codes()

        try:
            async with self._stock_master_maker() as session:
                # EDINETの3つのテーブル全てに存在する銘柄を取得
                # 配当データ
                stmt = select(func.distinct(EdinetStockDividend.sec_code))
                result = await session.execute(stmt)
                div_codes = set(result.scalars().all() or [])

                # P&Lデータ
                stmt = select(func.distinct(EdinetProfitAndLoss.sec_code))
                result = await session.execute(stmt)
                pl_codes = set(result.scalars().all() or [])

                # キャッシュフロー データ
                stmt = select(func.distinct(EdinetCashFlowStatement.sec_code))
                result = await session.execute(stmt)
                cf_codes = set(result.scalars().all() or [])

                # いずれかのテーブルに存在する銘柄を取得（AND条件）
                # 最も厳しい条件：すべてのテーブルに存在
                common_codes = div_codes & pl_codes & cf_codes
                return sorted(list(common_codes))
        except Exception as exc:
            logger.error("fetch sec codes with edinet data failed: %s", exc)
            return []

    async def _async_fetch_sector_code_17(self, sec_code: str) -> Optional[str]:
        """証券コードから17業種コードを取得。"""
        if self._stock_master_maker is None:
            return None
        try:
            async with self._stock_master_maker() as session:
                mapping_repo = StockCodeMappingRepository(session=session)
                mapping = await mapping_repo.get_by_sec_code(sec_code)
                if mapping:
                    return getattr(mapping, "sector_code_17", None)
        except Exception as e:
            logger.debug("failed to get sector_code_17 for %s: %s", sec_code, e)
        return None

    # pylint: disable=R0914
    async def run(self, sec_codes: Optional[List[str]], evaluation_date: date) -> None:
        """スクリーニングを実行して結果を出力。

        Args:
            sec_codes: 対象銘柄コードのリスト。None の場合は全銘柄を取得
            evaluation_date: 評価実行日
        """
        if sec_codes is None:
            # 全銘柄をスクリーニング対象にする
            sec_codes = await self._async_fetch_all_stock_master_codes()

        print(f"[{evaluation_date}] スクリーニング結果")
        passed_count = 0
        failed_count = 0
        skipped_count = 0
        total = len(sec_codes)

        for code in sec_codes:
            # EDINET データ存在チェック
            if self._stock_master_maker is not None:
                try:
                    async with self._stock_master_maker() as session:
                        has_data = False
                        for model_class in (
                            EdinetStockDividend,
                            EdinetProfitAndLoss,
                            EdinetCashFlowStatement,
                        ):
                            stmt = select(model_class).where(model_class.sec_code == code).limit(1)
                            r = await session.execute(stmt)
                            if r.scalar_one_or_none() is not None:
                                has_data = True
                                break

                        if not has_data:
                            logger.debug("skip %s: no EDINET data", code)
                            skipped_count += 1
                            continue
                except Exception as e:
                    logger.debug("edinet data check failed for %s: %s; proceeding", code, e)

            # スクリーニング評価
            # (業種別ストラテジーは evaluate() メソッド内で自動適用)
            res = await self.evaluate(code, evaluation_date)
            await self._persist_result(res, evaluation_date)

            # 結果集計
            if res.status in ("priority", "active", "watch"):
                passed_count += 1
            else:
                failed_count += 1

        # 統計情報を出力
        stats_msg = (
            f"--- 合格 {passed_count}件 / 不合格 {failed_count}件 / "
            f"スキップ {skipped_count}件 / 全体 {total}件 ---"
        )
        print(stats_msg)

    async def evaluate(self, sec_code: str, evaluation_date: date) -> ScreeningResult:
        """単一銘柄をスクリーニング評価。

        Args:
            sec_code: 証券コード
            evaluation_date: 評価実行日

        Returns:
            ScreeningResult
        """
        # 業種コード（17業種）を取得
        industry_code = await self._async_fetch_sector_code_17(sec_code)
        if not industry_code:
            industry_code = "33"  # デフォルトはサービス業

        # 業種に対応するストラテジーを取得
        try:
            strategy = self._strategy_factory.create(industry_code)
        except ValueError:
            logger.warning(
                "Unknown industry_code %s for sec_code %s; using default",
                industry_code,
                sec_code,
            )
            industry_code = "33"
            strategy = self._strategy_factory.create(industry_code)

        # 履歴データ取得
        divs = list(await self._call_history("get_dividend_history", sec_code) or [])
        eps = list(await self._call_history("get_eps_history", sec_code) or [])
        cfs = list(await self._call_history("get_operating_cf_history", sec_code) or [])
        stabs = list(await self._call_history("get_stability_history", sec_code) or [])

        # ストラテジーで評価
        result = await strategy.evaluate_with_history(
            sec_code=sec_code,
            evaluation_date=evaluation_date,
            divs=divs,
            eps=eps,
            cfs=cfs,
            stabs=stabs,
        )

        return result

    async def _call_history(self, method_name: str, sec_code: str) -> Any:
        """FinancialQueryService のメソッドを呼び出し。"""
        method = getattr(self._fq, method_name)
        result = method(sec_code, years=5)
        if inspect.isawaitable(result):
            return await result
        return result

    async def _persist_result(self, result: ScreeningResult, evaluation_date: date) -> None:
        """スクリーニング結果をDB に保存。"""
        maker = self._screening_result_maker
        if maker is None:
            return

        payload = self._build_upsert_payload(result, evaluation_date)
        try:
            async with maker.begin() as session:
                try:
                    mapping_repo = StockCodeMappingRepository(session=session)
                    mapping = await mapping_repo.get_by_sec_code(result.sec_code)
                    if mapping and getattr(mapping, "stock_code", None):
                        payload["symbol"] = mapping.stock_code
                    else:
                        payload["symbol"] = result.sec_code
                except Exception:
                    payload.setdefault("symbol", result.sec_code)

                repo = self._screening_result_factory(session)
                await repo.upsert(payload)
        except Exception:
            logger.exception("Failed to persist screening result for %s", result.sec_code)

    def _build_upsert_payload(
        self, result: ScreeningResult, evaluation_date: date
    ) -> Dict[str, Any]:
        """DB 保存用のペイロードを構築。"""
        return {
            "evaluation_year": evaluation_date.year,
            "fiscal_year_end": result.fiscal_year_end,
            "pass_required_conditions": result.pass_required,
            "total_score": result.total_score,
            "score_dividend": result.score_dividend,
            "score_eps": result.score_eps,
            "score_stability": result.score_stability,
            "score_profitability": result.score_profitability,
            "status": result.status,
            "failed_conditions": result.failed_conditions or [],
            "screening_details": self._build_screening_details(result),
        }

    @staticmethod
    def _build_screening_details(result: ScreeningResult) -> Dict[str, Any]:
        """スクリーニング詳細情報を構築。"""
        return {
            "score_breakdown": {
                "dividend": result.score_dividend,
                "eps": result.score_eps,
                "stability": result.score_stability,
                "profitability": result.score_profitability,
            },
            "status": result.status,
            "pass_required": result.pass_required,
            "failed_conditions": result.failed_conditions or [],
            "fiscal_year_end": (
                result.fiscal_year_end.isoformat() if result.fiscal_year_end is not None else None
            ),
        }
