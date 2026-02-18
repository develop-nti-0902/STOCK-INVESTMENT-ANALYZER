import asyncio
from datetime import date
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.market_data.edinet.edinet_cash_flow_statement import EdinetCashFlowStatement
from app.models.market_data.edinet.edinet_profit_and_loss import EdinetProfitAndLoss
from app.models.market_data.edinet.edinet_stock_dividend import EdinetStockDividend
from app.repositories.market_data.stock_master.stock_master_repository import StockMasterRepository
from app.services.market_data.stock_master.service import StockMasterService
from app.services.screening.simple_screening_service import SimpleScreeningService
from app.utils.database import get_engine
from app.utils.stock_code_converter import to_edinet_code


class DbFinancialQueryAdapter:
    """実DBから履歴を取得して FinancialQueryService と互換のインターフェースを提供するアダプタ。

    内部で非同期セッションを作成し、`asyncio.run` でクエリを実行して同期メソッドを提供します。
    """

    def __init__(self):
        self._engine = get_engine()
        self._maker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    def _run(self, coro):
        try:
            # 実行に長時間かかった場合に備えタイムアウトを設定
            return asyncio.run(asyncio.wait_for(coro, timeout=20))
        except asyncio.TimeoutError:
            print("[DEBUG] DB coroutine timed out")
            raise

    def list_dividends(self, sec_code: str):
        async def _inner():
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
                out = []
                for r in rows:
                    out.append(
                        SimpleNamespace(
                            fiscal_year_end=r.period_end_date,
                            dividend_per_share=(
                                float(r.dividend_actual) if r.dividend_actual is not None else 0.0
                            ),
                        )
                    )
                print(f"[DEBUG] list_dividends end sec_code={sec_code}")
                return out

        return self._run(_inner())

    # --- SimpleScreeningService 互換メソッド ---
    def get_dividend_history(self, sec_code: str, years: int = 5):
        return self.list_dividends(sec_code)

    def get_eps_history(self, sec_code: str, years: int = 5):
        # FinancialQueryService の命名に合わせる
        records = self.list_profit_and_loss(sec_code)
        # 期待されるオブジェクトは `.eps` 属性を持つこと
        return [
            SimpleNamespace(fiscal_year_end=r.fiscal_year_end, eps=getattr(r, "eps", 0.0))
            for r in records
        ]

    def get_operating_cf_history(self, sec_code: str, years: int = 5):
        records = self.list_cash_flows(sec_code)
        return [
            SimpleNamespace(
                fiscal_year_end=r.fiscal_year_end, operating_cf=getattr(r, "operating_cf", 0.0)
            )
            for r in records
        ]

    def get_stability_history(self, sec_code: str, years: int = 5):
        records = self.list_profit_and_loss(sec_code)
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

    def list_profit_and_loss(self, sec_code: str):
        async def _inner():
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
                out = []
                for r in rows:
                    out.append(
                        SimpleNamespace(
                            fiscal_year_end=r.period_end_date,
                            eps=(float(r.eps) if r.eps is not None else 0.0),
                            net_sales=(float(r.net_sales) if r.net_sales is not None else 0.0),
                            operating_income=(
                                float(r.operating_income) if r.operating_income is not None else 0.0
                            ),
                        )
                    )
                print(f"[DEBUG] list_profit_and_loss end sec_code={sec_code}")
                return out

        return self._run(_inner())

    def list_cash_flows(self, sec_code: str):
        async def _inner():
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
                out = []
                for r in rows:
                    out.append(
                        SimpleNamespace(
                            fiscal_year_end=r.period_end_date,
                            operating_cf=(
                                float(r.operating_cf) if r.operating_cf is not None else 0.0
                            ),
                        )
                    )
                print(f"[DEBUG] list_cash_flows end sec_code={sec_code}")
                return out

        return self._run(_inner())


def main():
    fq_adapter = DbFinancialQueryAdapter()
    svc = SimpleScreeningService(fq_adapter)
    try:
        # サービス内部で銘柄マスターを取得してスクリーニングを実行
        svc.run(None, date.today())
    except KeyboardInterrupt:
        print("[DEBUG] execution interrupted by user")
    finally:
        # 明示的にエンジンの接続を閉じてバックグラウンドスレッドを終了させる
        try:
            asyncio.run(get_engine().dispose())
            print("[DEBUG] engine disposed")
        except Exception as e:
            print(f"[DEBUG] engine dispose failed: {e}")


if __name__ == "__main__":
    main()
