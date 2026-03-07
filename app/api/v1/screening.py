"""新しいScreeningService対応 - スクリーニングAPI (v1).

業種別ストラテジーパターンに対応した新しいスクリーニングサービスのAPIエンドポイント。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies.services import get_screening_service
from app.models.market_data.edinet.edinet_cash_flow_statement import EdinetCashFlowStatement
from app.models.market_data.edinet.edinet_document import EdinetDocument
from app.models.market_data.edinet.edinet_profit_and_loss import EdinetProfitAndLoss
from app.models.market_data.edinet.edinet_stock_dividend import EdinetStockDividend
from app.repositories.screening import ScreeningResultRepository
from app.services.screening.screening_service import ScreeningService
from app.utils.database import get_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["screening"])


class DbFinancialQueryAdapter:
    """実DBから履歴を取得して FinancialQueryService と互換のインターフェースを提供するアダプタ。"""

    def __init__(self, maker: async_sessionmaker[AsyncSession]):
        self._maker = maker

    async def list_dividends(self, sec_code: str):
        async with self._maker() as s:
            stmt = (
                select(EdinetStockDividend)
                .join(EdinetDocument)
                .where(EdinetDocument.sec_code == sec_code)
                .order_by(EdinetStockDividend.period_end_date.asc())
            )
            res = await s.execute(stmt)
            rows = res.scalars().all()
            out = [
                SimpleNamespace(
                    fiscal_year_end=r.period_end_date,
                    dividend_per_share=(
                        float(r.dividend_adj) if r.dividend_adj is not None else 0.0
                    ),
                )
                for r in rows
            ]
        return out

    async def list_profit_and_loss(self, sec_code: str):
        async with self._maker() as s:
            stmt = (
                select(EdinetProfitAndLoss)
                .join(EdinetDocument)
                .where(EdinetDocument.sec_code == sec_code)
                .order_by(EdinetProfitAndLoss.period_end_date.asc())
            )
            res = await s.execute(stmt)
            rows = res.scalars().all()
            out = [
                SimpleNamespace(
                    fiscal_year_end=r.period_end_date,
                    eps=(float(r.eps) if r.eps is not None else 0.0),
                    net_sales=(float(r.net_sales) if r.net_sales is not None else 0.0),
                    operating_income=(
                        float(r.operating_income) if r.operating_income is not None else 0.0
                    ),
                )
                for r in rows
            ]
        return out

    async def list_cash_flows(self, sec_code: str):
        async with self._maker() as s:
            stmt = (
                select(EdinetCashFlowStatement)
                .join(EdinetDocument)
                .where(EdinetDocument.sec_code == sec_code)
                .order_by(EdinetCashFlowStatement.period_end_date.asc())
            )
            res = await s.execute(stmt)
            rows = res.scalars().all()
            out = [
                SimpleNamespace(
                    fiscal_year_end=r.period_end_date,
                    operating_cf=(float(r.operating_cf) if r.operating_cf is not None else 0.0),
                )
                for r in rows
            ]
        return out

    async def close(self) -> None:
        """エンジンのクリーンアップを行う。"""

    # --- FinancialQueryService 互換メソッド ---
    async def get_dividend_history(
        self, sec_code: str, years: int = 5
    ):  # pylint: disable=unused-argument
        return await self.list_dividends(sec_code)

    async def get_eps_history(
        self, sec_code: str, years: int = 5
    ):  # pylint: disable=unused-argument
        records = await self.list_profit_and_loss(sec_code)
        return [
            SimpleNamespace(fiscal_year_end=r.fiscal_year_end, eps=getattr(r, "eps", 0.0))
            for r in records
        ]

    async def get_operating_cf_history(
        self, sec_code: str, years: int = 5
    ):  # pylint: disable=unused-argument
        records = await self.list_cash_flows(sec_code)
        return [
            SimpleNamespace(
                fiscal_year_end=r.fiscal_year_end, operating_cf=getattr(r, "operating_cf", 0.0)
            )
            for r in records
        ]

    async def get_stability_history(
        self, sec_code: str, years: int = 5
    ):  # pylint: disable=unused-argument
        records = await self.list_profit_and_loss(sec_code)
        return [
            SimpleNamespace(
                fiscal_year_end=r.fiscal_year_end,
                net_sales=getattr(r, "net_sales", 0.0),
                operating_income=getattr(r, "operating_income", 0.0),
                operating_margin=(
                    getattr(r, "operating_income", 0.0) / getattr(r, "net_sales", 1.0)
                    if getattr(r, "net_sales", 0.0)
                    else 0.0
                ),
            )
            for r in records
        ]


@router.post("/run")
async def run_screening(
    sec_codes: Optional[list[str]] = None,
    evaluation_date: Optional[str] = None,
    screening_service: ScreeningService = Depends(get_screening_service),
) -> dict:
    """業種別ストラテジーを用いてスクリーニングを実行。

    Args:
        sec_codes: 対象銘柄コードのリスト。None の場合は全銘柄を対象。
        evaluation_date: 評価実行日 (ISO形式, 指定なしの場合は本日)
        screening_service: ScreeningService インスタンス（DI から自動取得）

    Returns:
        スクリーニング実行結果
    """
    try:
        if evaluation_date is None:
            eval_date = datetime.now().date()
        else:
            eval_date = datetime.fromisoformat(evaluation_date).date()

        # ScreeningService は DI で自動取得
        await screening_service.run(
            sec_codes=sec_codes,
            evaluation_date=eval_date,
        )

        # DB から今回実行したスクリーニング結果を取得
        engine = get_engine()
        maker = async_sessionmaker(bind=engine, expire_on_commit=False)

        async with maker() as session:
            repo = ScreeningResultRepository(session=session)
            screening_results = await repo.list()
            # 評価年でフィルタリング
            target_year = eval_date.year
            filtered_results = [
                r
                for r in screening_results
                if hasattr(r, "evaluation_year") and r.evaluation_year == target_year
            ]

            # モデルオブジェクトを辞書に変換
            results_as_dict = [
                {
                    "id": r.id,
                    "symbol": r.symbol,
                    "evaluation_year": r.evaluation_year if hasattr(r, "evaluation_year") else None,
                    "fiscal_year_end": r.fiscal_year_end.isoformat() if r.fiscal_year_end else None,
                    "pass_required_conditions": r.pass_required_conditions,
                    "total_score": r.total_score,
                    "score_dividend": r.score_dividend,
                    "score_eps": r.score_eps,
                    "score_stability": r.score_stability,
                    "score_profitability": r.score_profitability,
                    "status": r.status,
                    "failed_conditions": r.failed_conditions,
                    "screening_details": r.screening_details,
                }
                for r in filtered_results
            ]

        return {
            "status": "success",
            "result": results_as_dict,
            "evaluation_year": target_year,
        }
    except Exception as e:
        logger.error("Screening failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
