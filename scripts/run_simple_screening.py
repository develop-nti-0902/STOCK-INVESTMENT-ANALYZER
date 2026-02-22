import asyncio
from datetime import date
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.models.market_data.edinet.edinet_cash_flow_statement import EdinetCashFlowStatement
from app.models.market_data.edinet.edinet_profit_and_loss import EdinetProfitAndLoss
from app.models.market_data.edinet.edinet_stock_dividend import EdinetStockDividend
from app.repositories.screening.screening_result_repository import ScreeningResultRepository
from app.services.screening.simple_screening_service import SimpleScreeningService
from app.utils.database import get_database_url


class DbFinancialQueryAdapter:
    """実DBから履歴を取得して FinancialQueryService と互換のインターフェースを提供するアダプタ。"""

    def __init__(self, engine, maker: async_sessionmaker[AsyncSession]):
        self._engine = engine
        self._maker = maker

    async def list_dividends(self, sec_code: str):
        print(f"[DEBUG] list_dividends start sec_code={sec_code}")
        async with self._maker() as s:
            stmt = (
                select(EdinetStockDividend)
                .where(EdinetStockDividend.sec_code == sec_code)
                .order_by(EdinetStockDividend.period_end_date.asc())
            )
            res = await s.execute(stmt)
            rows = res.scalars().all()
            print(f"[DEBUG] list_dividends fetched rows={len(rows)} sec_code={sec_code}")
            out = [
                SimpleNamespace(
                    fiscal_year_end=r.period_end_date,
                    dividend_per_share=(
                        float(r.dividend_adj) if r.dividend_adj is not None else 0.0
                    ),
                )
                for r in rows
            ]
        print(f"[DEBUG] list_dividends end sec_code={sec_code}")
        return out

    async def list_profit_and_loss(self, sec_code: str):
        print(f"[DEBUG] list_profit_and_loss start sec_code={sec_code}")
        async with self._maker() as s:
            stmt = (
                select(EdinetProfitAndLoss)
                .where(EdinetProfitAndLoss.sec_code == sec_code)
                .order_by(EdinetProfitAndLoss.period_end_date.asc())
            )
            res = await s.execute(stmt)
            rows = res.scalars().all()
            print(f"[DEBUG] list_profit_and_loss fetched rows={len(rows)} sec_code={sec_code}")
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
        print(f"[DEBUG] list_profit_and_loss end sec_code={sec_code}")
        return out

    async def list_cash_flows(self, sec_code: str):
        print(f"[DEBUG] list_cash_flows start sec_code={sec_code}")
        async with self._maker() as s:
            stmt = (
                select(EdinetCashFlowStatement)
                .where(EdinetCashFlowStatement.sec_code == sec_code)
                .order_by(EdinetCashFlowStatement.period_end_date.asc())
            )
            res = await s.execute(stmt)
            rows = res.scalars().all()
            print(f"[DEBUG] list_cash_flows fetched rows={len(rows)} sec_code={sec_code}")
            out = [
                SimpleNamespace(
                    fiscal_year_end=r.period_end_date,
                    operating_cf=(float(r.operating_cf) if r.operating_cf is not None else 0.0),
                )
                for r in rows
            ]
        print(f"[DEBUG] list_cash_flows end sec_code={sec_code}")
        return out

    async def close(self) -> None:
        """エンジンのクリーンアップを行う。

        NullPoolを使用しているため、dispose()は不要。
        """
        pass

    # --- SimpleScreeningService 互換メソッド ---
    async def get_dividend_history(self, sec_code: str, years: int = 5):
        return await self.list_dividends(sec_code)

    async def get_eps_history(self, sec_code: str, years: int = 5):
        records = await self.list_profit_and_loss(sec_code)
        return [
            SimpleNamespace(fiscal_year_end=r.fiscal_year_end, eps=getattr(r, "eps", 0.0))
            for r in records
        ]

    async def get_operating_cf_history(self, sec_code: str, years: int = 5):
        records = await self.list_cash_flows(sec_code)
        return [
            SimpleNamespace(
                fiscal_year_end=r.fiscal_year_end, operating_cf=getattr(r, "operating_cf", 0.0)
            )
            for r in records
        ]

    async def get_stability_history(self, sec_code: str, years: int = 5):
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


async def main():
    # NullPoolを使用してスレッドプール問題を回避
    engine = create_async_engine(get_database_url(), poolclass=NullPool, echo=False)
    maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    fq_adapter = DbFinancialQueryAdapter(engine=engine, maker=maker)
    svc = SimpleScreeningService(
        fq_adapter,
        stock_master_maker=maker,
        screening_result_maker=maker,
        screening_result_factory=lambda session: ScreeningResultRepository(session),
    )
    try:
        # サービス内部で銘柄マスターを取得してスクリーニングを実行
        await svc.run(None, date.today())
    except KeyboardInterrupt:
        print("[DEBUG] execution interrupted by user")
    finally:
        try:
            await fq_adapter.close()
            print("[DEBUG] adapter closed")
        except Exception as e:
            print(f"[DEBUG] adapter close failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
