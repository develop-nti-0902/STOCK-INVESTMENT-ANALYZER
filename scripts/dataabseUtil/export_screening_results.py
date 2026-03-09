"""SCREENING_RESULTS から指定条件で抽出し CSV 出力するユーティリティスクリプト.

使い方の例:
    poetry run python -m scripts.dataabseUtil.export_screening_results --status active --year 2025 --out out.csv

引数:
    --status: フィルタするスクリーニング判定 (active|watch|not_eligible)。未指定で全件。
    --year: 評価年度 (西暦、必須)
    --out: 出力CSVファイルパス。指定なければ自動生成。

出力カラム:
  銘柄コード（stock_code）, 企業名, 業種コード（33分類）, 業種名（33分類）, 評価年度（西暦）, 会計年度末,
  必須条件判定, 総合スコア, 配当スコア, EPS スコア, 安定性スコア, 収益性スコア, スクリーニング判定, yfinanceURL
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.market_data.stock_master.sector_33_master import Sector33Master
from app.models.market_data.stock_master.stock_master import StockMaster
from app.models.screening import ScreeningResult
from app.utils.database import get_engine

CSV_HEADERS = [
    "銘柄コード（stock_code）",
    "企業名",
    "業種コード（33分類）",
    "業種名（33分類）",
    "評価年度（西暦）",
    "会計年度末",
    "必須条件判定",
    "総合スコア",
    "配当スコア",
    "EPS スコア",
    "安定性スコア",
    "収益性スコア",
    "スクリーニング判定",
    "yfinanceURL",
]


def build_yfinance_url(symbol: str) -> str:
    # symbol は銘柄コードの数値部分（例: 7203）を想定
    return f"https://finance.yahoo.co.jp/quote/{symbol}.T"


async def export_csv(status: Optional[str], year: int, out_path: str) -> None:
    engine = get_engine()
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with maker() as session:
        # ScreeningResult を StockMaster / Sector33 と外部結合して取得
        stmt = (
            select(ScreeningResult, StockMaster, Sector33Master)
            .outerjoin(StockMaster, StockMaster.stock_code == ScreeningResult.symbol)
            .outerjoin(Sector33Master, StockMaster.sector_33_id == Sector33Master.id)
        )

        stmt = stmt.where(ScreeningResult.evaluation_year == year)
        if status:
            stmt = stmt.where(ScreeningResult.status == status)

        stmt = stmt.order_by(
            ScreeningResult.total_score.desc().nullslast(), ScreeningResult.evaluation_year.desc()
        )

        result = await session.execute(stmt)
        rows = result.all()

        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)

            for sr, sm, s33 in rows:
                stock_code = None
                stock_name = None
                sector_code = None
                sector_name = None

                if sm is not None:
                    stock_code = getattr(sm, "stock_code", None)
                    stock_name = getattr(sm, "stock_name", None)
                    if getattr(sm, "sector_33", None) is not None:
                        # relationship が遅延ロードされている可能性があるが
                        # セレクトで s33 を取得しているため s33 が優先
                        pass
                # フォールバック: ScreeningResult の symbol を stock_code として利用
                if not stock_code:
                    stock_code = getattr(sr, "symbol", None)

                if s33 is not None:
                    sector_code = getattr(s33, "code", None)
                    sector_name = getattr(s33, "name", None)
                else:
                    # try relationship from stock master if available
                    if sm is not None and getattr(sm, "sector_33", None) is not None:
                        sector_code = getattr(sm.sector_33, "code", None)
                        sector_name = getattr(sm.sector_33, "name", None)

                fiscal_year_end = (
                    sr.fiscal_year_end.isoformat() if getattr(sr, "fiscal_year_end", None) else ""
                )
                pass_required = getattr(sr, "pass_required_conditions", None)

                total = getattr(sr, "total_score", "")
                sd = getattr(sr, "score_dividend", "")
                seps = getattr(sr, "score_eps", "")
                sstab = getattr(sr, "score_stability", "")
                sprof = getattr(sr, "score_profitability", "")
                screening_status = getattr(sr, "status", "")

                yurl = build_yfinance_url(stock_code) if stock_code else ""

                writer.writerow(
                    [
                        stock_code or "",
                        stock_name or "",
                        sector_code or "",
                        sector_name or "",
                        year,
                        fiscal_year_end,
                        pass_required,
                        total,
                        sd,
                        seps,
                        sstab,
                        sprof,
                        screening_status,
                        yurl,
                    ]
                )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export screening_results to CSV")
    p.add_argument(
        "--status",
        choices=["active", "watch", "not_eligible"],
        help="フィルタするスクリーニング判定（省略すると全件）",
    )
    p.add_argument("--year", required=True, type=int, help="評価年度（西暦、必須）")
    p.add_argument("--out", required=False, help="出力CSVファイルパス（デフォルト生成）")
    return p.parse_args()


def make_default_out(year: int, status: Optional[str]) -> str:
    status_part = status if status else "all"
    return f"screening_results_{year}_{status_part}.csv"


def main() -> None:
    args = parse_args()
    out_path = args.out or make_default_out(args.year, args.status)
    asyncio.run(export_csv(args.status, args.year, out_path))


if __name__ == "__main__":
    main()
