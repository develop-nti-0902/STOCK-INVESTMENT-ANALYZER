"""新しいスクリーニングサービス - Strategyパターン対応版。

業種別スクリーニングルールをサポートする新しいサービス実装です。
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Set

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload

from app.exceptions.system import ConfigurationError
from app.models.market_data.edinet.edinet_cash_flow_statement import EdinetCashFlowStatement
from app.models.market_data.edinet.edinet_document import EdinetDocument
from app.models.market_data.edinet.edinet_profit_and_loss import EdinetProfitAndLoss
from app.models.market_data.edinet.edinet_stock_dividend import EdinetStockDividend
from app.models.market_data.stock_master import StockCodeMapping, StockMaster
from app.models.market_data.stock_master.sector_33_master import Sector33Master
from app.repositories.market_data.stock_master import (
    StockCodeMappingRepository,
    StockMasterRepository,
)
from app.repositories.market_data.stock_master.sector_33_master_repository import (
    Sector33MasterRepository,
)
from app.repositories.screening.screening_result_repository import ScreeningResultRepository
from app.services.data_synchronization.market_data.stock_master.service import StockMasterService
from app.services.screening.models import ScreeningConfig, ScreeningResult
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
        sector_33_master_repo: Optional[Sector33MasterRepository] = None,
    ):
        """初期化。

        Args:
            financial_query_service: 財務データ取得サービス
            stock_master_maker: 銘柄マスター用のセッションメーカー
            screening_result_maker: スクリーニング結果用のセッションメーカー
            screening_result_factory: ScreeningResultRepository ファクトリ
            sector_33_master_repo: 業種マスター Repository (DI用)
        """
        self._fq = financial_query_service
        self._stock_master_maker = stock_master_maker
        self._screening_result_maker = screening_result_maker
        self._screening_result_factory = screening_result_factory
        self._sector_33_master_repo = sector_33_master_repo
        self._strategy_factory = ScreeningStrategyFactory()
        self._industry_config_cache: Dict[str, ScreeningConfig] = {}

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
                stmt = select(func.distinct(EdinetDocument.sec_code)).join(
                    EdinetStockDividend,
                    EdinetStockDividend.edinet_document_id == EdinetDocument.id,
                )
                result = await session.execute(stmt)
                div_codes = set(result.scalars().all() or [])

                # P&Lデータ
                stmt = select(func.distinct(EdinetDocument.sec_code)).join(
                    EdinetProfitAndLoss,
                    EdinetProfitAndLoss.edinet_document_id == EdinetDocument.id,
                )
                result = await session.execute(stmt)
                pl_codes = set(result.scalars().all() or [])

                # キャッシュフロー データ
                stmt = select(func.distinct(EdinetDocument.sec_code)).join(
                    EdinetCashFlowStatement,
                    EdinetCashFlowStatement.edinet_document_id == EdinetDocument.id,
                )
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
        """証券コードから17業種コードを取得。

        修正: StockCodeMapping → StockMaster → sector_17 ForeignKey を通じて取得
        """
        if self._stock_master_maker is None:
            return None
        try:
            async with self._stock_master_maker() as session:
                # 1. sec_code から StockCodeMapping を取得
                mapping_repo = StockCodeMappingRepository(session=session)
                mapping = await mapping_repo.get_by_sec_code(sec_code)
                if not mapping:
                    return None

                # 2. stock_code から StockMaster を取得（sector_17 FK を eager load）
                stock_repo = StockMasterRepository(session=session)
                stmt = (
                    select(stock_repo.model)
                    .where(stock_repo.model.stock_code == mapping.stock_code)
                    .options(joinedload(stock_repo.model.sector_17))
                )

                result = await session.execute(stmt)
                stock = result.scalar_one_or_none()

                if stock and stock.sector_17:
                    return stock.sector_17.code
        except Exception as e:
            logger.debug("failed to get sector_code_17 for %s: %s", sec_code, e)
        return None

    async def _async_fetch_sec_code_to_sector_33_mapping(
        self, sec_codes: List[str]
    ) -> Dict[str, str]:
        """複数の証券コードから sector_33_code へのマッピングを一括取得（1-query JOIN）。

        Args:
            sec_codes: 証券コードのリスト

        Returns:
            Dict[str, str]: sec_code -> sector_33_code のマッピング
        """
        if self._stock_master_maker is None or not sec_codes:
            return {}

        try:
            async with self._stock_master_maker() as session:
                # StockCodeMapping + StockMaster + Sector33Master を JOIN して1クエリで取得
                stmt = (
                    select(
                        StockCodeMapping.sec_code,
                        Sector33Master.code.label("sector_33_code"),
                    )
                    .join(StockMaster, StockMaster.stock_code == StockCodeMapping.stock_code)
                    .join(Sector33Master, Sector33Master.id == StockMaster.sector_33_id)
                    .where(StockCodeMapping.sec_code.in_(sec_codes))
                )

                result = await session.execute(stmt)
                rows = result.all()

                pairs = [(row[0], row[1]) for row in rows]
                return dict(pairs)
        except Exception as exc:
            logger.error("fetch sec_code to sector_33 mapping failed: %s", exc)
            return {}

    async def _async_fetch_sec_code_to_stock_code_mapping(
        self, sec_codes: List[str]
    ) -> Dict[str, str]:
        """複数の証券コードから stock_code へのマッピングを一括取得。

        保存時に逆引きするための映射を事前取得することで、保存時のDB参照を削減します。

        Args:
            sec_codes: 証券コードのリスト

        Returns:
            Dict[str, str]: sec_code -> stock_code のマッピング
        """
        if self._stock_master_maker is None or not sec_codes:
            return {}

        try:
            async with self._stock_master_maker() as session:
                stmt = select(StockCodeMapping.sec_code, StockCodeMapping.stock_code).where(
                    StockCodeMapping.sec_code.in_(sec_codes)
                )
                result = await session.execute(stmt)
                rows = result.all()
                pairs = [(row[0], row[1]) for row in rows]
                return dict(pairs)
        except Exception as exc:
            logger.error("fetch sec_code to stock_code mapping failed: %s", exc)
            return {}

    async def _async_fetch_edinet_codes_set(self) -> Set[str]:
        """EDINETデータが存在する証券コードのセットを一括取得。

        3つのEDINETテーブル（配当、P&L、キャッシュフロー）すべてに存在する
        証券コードを返します。（AND条件）

        Returns:
            Set[str]: EDINET データが存在する sec_code のセット
        """
        if self._stock_master_maker is None:
            return set()

        try:
            async with self._stock_master_maker() as session:
                # 配当データ
                stmt = select(func.distinct(EdinetDocument.sec_code)).join(
                    EdinetStockDividend,
                    EdinetStockDividend.edinet_document_id == EdinetDocument.id,
                )
                result = await session.execute(stmt)
                div_codes = set(result.scalars().all() or [])

                # P&L データ
                stmt = select(func.distinct(EdinetDocument.sec_code)).join(
                    EdinetProfitAndLoss,
                    EdinetProfitAndLoss.edinet_document_id == EdinetDocument.id,
                )
                result = await session.execute(stmt)
                pl_codes = set(result.scalars().all() or [])

                # キャッシュフロー データ
                stmt = select(func.distinct(EdinetDocument.sec_code)).join(
                    EdinetCashFlowStatement,
                    EdinetCashFlowStatement.edinet_document_id == EdinetDocument.id,
                )
                result = await session.execute(stmt)
                cf_codes = set(result.scalars().all() or [])

                # 3つのテーブル全てに存在する銘柄を返す（AND条件で全に存在必須）
                common_codes = div_codes & pl_codes & cf_codes
                return common_codes
        except Exception as exc:
            logger.error("fetch edinet codes set failed: %s", exc)
            return set()

    # pylint: disable=R0914
    async def run(self, sec_codes: Optional[List[str]], evaluation_date: date) -> None:
        """スクリーニングを実行して結果を出力。業種単位でバッチ処理。

        Args:
            sec_codes: 対象銘柄コードのリスト。None の場合は全銘柄を取得
            evaluation_date: 評価実行日
        """
        if sec_codes is None:
            # 全銘柄をスクリーニング対象にする
            sec_codes = await self._async_fetch_all_stock_master_codes()

        print(f"[{evaluation_date}] スクリーニング結果")

        # 事前に必要なデータを一括取得
        sector_33_mapping = await self._async_fetch_sec_code_to_sector_33_mapping(sec_codes)
        sec_to_stock_mapping = await self._async_fetch_sec_code_to_stock_code_mapping(sec_codes)
        edinet_codes_set = await self._async_fetch_edinet_codes_set()

        # sec_code を sector_33_code でグループ化
        grouped_by_sector: Dict[str, List[str]] = {}
        for code in sec_codes:
            sector_33 = sector_33_mapping.get(code, "33")  # デフォルト
            if sector_33 not in grouped_by_sector:
                grouped_by_sector[sector_33] = []
            grouped_by_sector[sector_33].append(code)

        # 業種別統計
        sector_stats: Dict[str, Dict[str, int]] = {}
        total_passed = 0
        total_failed = 0
        total_skipped = 0

        # 業種単位で処理（並列化は最大 4 業種同時）
        semaphore = asyncio.Semaphore(4)

        async def process_sector(sector_33_code: str, codes: List[str]) -> None:
            """業種単位の処理。"""
            nonlocal total_passed, total_failed, total_skipped

            async with semaphore:
                passed, failed, skipped = await self._process_sector(
                    sector_33_code,
                    codes,
                    edinet_codes_set,
                    evaluation_date,
                    sec_to_stock_mapping,
                )
                sector_stats[sector_33_code] = {
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                }
                total_passed += passed
                total_failed += failed
                total_skipped += skipped

        # 全業種を並列処理
        await asyncio.gather(
            *[
                process_sector(sector_33_code, codes)
                for sector_33_code, codes in grouped_by_sector.items()
            ]
        )

        # 業種別統計を出力
        if sector_stats:
            logger.info("--- 業種別スクリーニング統計 ---")
            for sector_code, stats in sorted(sector_stats.items()):
                logger.info(
                    "  Sector %s: 合格 %d件 / 不合格 %d件 / スキップ %d件",
                    sector_code,
                    stats["passed"],
                    stats["failed"],
                    stats["skipped"],
                )

        # 全体統計
        total = len(sec_codes)
        stats_msg = (
            f"--- 合格 {total_passed}件 / 不合格 {total_failed}件 / "
            f"スキップ {total_skipped}件 / 全体 {total}件 ---"
        )
        print(stats_msg)

    async def _process_sector(  # pylint: disable=R0912
        self,
        sector_33_code: str,
        sec_codes: List[str],
        edinet_codes_set: Set[str],
        evaluation_date: date,
        sec_to_stock_mapping: Dict[str, str],
    ) -> tuple[int, int, int]:
        """業種単位の処理。業種内銘柄を並列評価し、結果をまとめて保存。

        - 一部の銘柄評価失敗が全体を失敗させない（部分的な例外を個別扱い）
        - sector_33_code をオーバーライドとして evaluate に渡す

        Args:
            sector_33_code: 業種コード（Sector33Master.code）
            sec_codes: 証券コードのリスト
            edinet_codes_set: EDINET データが存在する証券コードのセット
            evaluation_date: 評価実行日
            sec_to_stock_mapping: sec_code -> stock_code のマッピング(保存高速化用)

        Returns:
            (passed_count, failed_count, skipped_count)
        """
        passed_count = 0
        failed_count = 0
        skipped_count = 0

        # EDINET 存在チェック（事前フィルタ）
        codes_with_edinet = [c for c in sec_codes if c in edinet_codes_set]
        skipped_count = len(sec_codes) - len(codes_with_edinet)

        if not codes_with_edinet:
            logger.debug("skip sector %s: no codes with edinet data", sector_33_code)
            return passed_count, failed_count, skipped_count

        # 業種内銘柄を並列評価（最大 8 同時）
        sem = asyncio.Semaphore(8)

        async def evaluate_and_build(
            code: str,
        ) -> tuple[str, Optional[ScreeningResult], Optional[Exception]]:
            """銘柄を評価。例外は tuple に含める。"""
            async with sem:
                try:
                    result = await self.evaluate(
                        code, evaluation_date, industry_code_override=sector_33_code
                    )
                    return code, result, None
                except Exception as e:
                    logger.debug(
                        "evaluate failed for code %s in sector %s: %s", code, sector_33_code, e
                    )
                    return code, None, e

        results = await asyncio.gather(
            *[evaluate_and_build(code) for code in codes_with_edinet],
            return_exceptions=False,
        )

        # 業種単位でトランザクション開始して結果を保存
        if self._screening_result_maker is not None:
            try:
                async with self._screening_result_maker.begin() as session:
                    for code, result, error in results:
                        if error:
                            # 評価失敗は失敗扱いに計上するが、トランザクション全体は続行
                            logger.warning(
                                "skip saving result for code %s: evaluation failed", code
                            )
                            failed_count += 1
                            continue

                        if result is None:
                            # 型安全のためのガード（通常はここに来ないはず）
                            logger.warning("skip saving result for code %s: no result", code)
                            failed_count += 1
                            continue

                        try:
                            # sec_to_stock_mapping から stock_code を取得（DB参照回避）
                            await self._persist_result_internal(
                                result, evaluation_date, session, sec_to_stock_mapping
                            )

                            # 結果集計
                            if result.status in ("priority", "active", "watch"):
                                passed_count += 1
                            else:
                                failed_count += 1
                        except Exception as e:
                            logger.warning("failed to persist code %s: %s", code, e)
                            failed_count += 1
            except Exception as e:
                logger.error("failed to persist results for sector %s: %s", sector_33_code, e)
                # トランザクション失敗時は各銘柄をすべて失敗に変更
                passed_count = 0
                failed_count = len(codes_with_edinet)
        else:
            # maker がない場合は評価結果のみ集計
            for code, result, error in results:
                if error:
                    failed_count += 1
                    continue

                if result is None:
                    failed_count += 1
                    continue

                if result.status in ("priority", "active", "watch"):
                    passed_count += 1
                else:
                    failed_count += 1

        return passed_count, failed_count, skipped_count

    async def _persist_result_internal(
        self,
        result: ScreeningResult,
        evaluation_date: date,
        session: AsyncSession,
        sec_to_stock_mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        """スクリーニング結果をDB に保存（既存セッション使用）。

        Args:
            result: スクリーニング結果
            evaluation_date: 評価実行日
            session: SQLAlchemy AsyncSession（トランザクション内で使用）
            sec_to_stock_mapping: 事前取得した sec_code -> stock_code マッピング(オプション)
        """
        payload = self._build_upsert_payload(result, evaluation_date)

        # 事前マッピングがある場合はそれを使用、なければDB参照
        if sec_to_stock_mapping and result.sec_code in sec_to_stock_mapping:
            payload["symbol"] = sec_to_stock_mapping[result.sec_code]
        else:
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

    async def evaluate(
        self, sec_code: str, evaluation_date: date, industry_code_override: Optional[str] = None
    ) -> ScreeningResult:
        """単一銘柄をスクリーニング評価。

        Args:
            sec_code: 証券コード
            evaluation_date: 評価実行日
            industry_code_override: 業種コード（指定時はこれを優先）

        Returns:
            ScreeningResult
        """
        # 業種コードを決定：オーバーライドがあればそれを使用、なければDB から取得
        if industry_code_override:
            industry_code: str = industry_code_override
        else:
            fetched_code = await self._async_fetch_sector_code_17(sec_code)
            industry_code = fetched_code if fetched_code else "33"

        # 業種に対応するストラテジーを取得
        try:
            strategy = self._strategy_factory.create(industry_code, screening_service=self)
        except ValueError:
            logger.warning(
                "Unknown industry_code %s for sec_code %s; using default",
                industry_code,
                sec_code,
            )
            industry_code = "33"
            strategy = self._strategy_factory.create(industry_code, screening_service=self)

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

    async def _init_industry_config_cache(self) -> None:
        """業種設定をキャッシュに初期化。

        Sector33MasterRepository から全業種設定を DB 経由で取得し、
        内部キャッシュ `_industry_config_cache` に保存します。

        DB 読み込み失敗時は ConfigurationError を発生させます。
        キャッシュが空の場合は警告ログを出力します。

        Raises:
            ConfigurationError: DB 読み込み失敗時
        """
        if self._sector_33_master_repo is None:
            logger.warning("Sector33MasterRepository not injected; skipping cache initialization")
            return

        try:
            self._industry_config_cache = await self._sector_33_master_repo.as_config_dict()
            if not self._industry_config_cache:
                logger.warning("Industry config cache is empty; no industry configurations loaded")
        except Exception as exc:
            msg = f"Failed to initialize industry config cache: {exc}"
            logger.error(msg)
            raise ConfigurationError(message=msg, context={"cause": str(exc)}) from exc

    def get_industry_config_dict(self) -> Dict[str, ScreeningConfig]:
        """キャッシュされた業種設定辞書を返す。

        Returns:
            Dict[str, ScreeningConfig]: 業種コードをキーとしたスクリーニング設定辞書
        """
        return self._industry_config_cache

    def get_industry_config(self, industry_code: str) -> Optional[ScreeningConfig]:
        """特定業種のスクリーニング設定を取得。

        Args:
            industry_code (str): 業種コード

        Returns:
            Optional[ScreeningConfig]: 見つかれば ScreeningConfig、なければ None
        """
        return self._industry_config_cache.get(industry_code)
