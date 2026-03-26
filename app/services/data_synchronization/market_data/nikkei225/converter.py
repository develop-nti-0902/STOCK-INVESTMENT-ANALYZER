"""日経225データ変換モジュール.

yfinance DataFrame から Pydantic スキーマリストへの変換を行います。
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.schemas.market_data.nikkei225 import Nikkei2251dCreate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Nikkei225Converter:
    """DataFrame → Nikkei2251dCreate リスト変換クラス."""

    def from_dataframe(self, df: pd.DataFrame) -> list[Nikkei2251dCreate]:
        """yfinance DataFrame から Pydantic スキーマリストを生成する.

        カラムマッピング:
            Open        → open
            High        → high
            Low         → low
            Close       → close
            Adj Close   → adj_close  (存在しない場合は None)
            Volume      → volume
            index       → timestamp  (JST 変換済み)

        Args:
            df: yfinance が返した DataFrame

        Returns:
            list[Nikkei2251dCreate]
        """
        if df.empty:
            return []

        # MultiIndex の場合は第1レベル（Price）のみに落とす
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.get_level_values(0)

        records: list[Nikkei2251dCreate] = []
        skipped = 0

        for idx, row in df.iterrows():
            # OHLC が NaN の行はスキップ
            open_val = row.get("Open")
            high_val = row.get("High")
            low_val = row.get("Low")
            close_val = row.get("Close")

            if (
                open_val is None
                or high_val is None
                or low_val is None
                or close_val is None
                or pd.isna(open_val)
                or pd.isna(high_val)
                or pd.isna(low_val)
                or pd.isna(close_val)
            ):
                skipped += 1
                continue

            # timestamp の JST 変換
            ts = pd.Timestamp(idx)
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC").tz_convert("Asia/Tokyo")
            else:
                ts = ts.tz_convert("Asia/Tokyo")

            # Adj Close（存在しない or NaN の場合は None）
            adj_raw = row.get("Adj Close")
            adj_close_val: float | None = (
                float(adj_raw) if adj_raw is not None and not pd.isna(adj_raw) else None
            )

            # Volume（NaN → 0）
            vol_raw = row.get("Volume")
            volume_val = int(float(vol_raw)) if vol_raw is not None and not pd.isna(vol_raw) else 0

            records.append(
                Nikkei2251dCreate(
                    timestamp=ts.to_pydatetime(),
                    open=float(open_val),
                    high=float(high_val),
                    low=float(low_val),
                    close=float(close_val),
                    adj_close=adj_close_val,
                    volume=volume_val,
                )
            )

        if skipped:
            logger.warning("Skipped %d rows with NaN OHLC values", skipped)

        logger.info("Converted %d records from DataFrame", len(records))
        return records

    def to_saver_records(self, models: list[Nikkei2251dCreate]) -> list[dict[str, Any]]:
        """Pydantic モデルリスト → Saver 用辞書リストに変換.

        Args:
            models: Nikkei2251dCreate のリスト

        Returns:
            list[dict]: Saver が受け取るレコード辞書のリスト
        """
        return [m.model_dump() for m in models]
