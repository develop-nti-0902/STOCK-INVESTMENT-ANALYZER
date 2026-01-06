import logging
from typing import Any, Optional

import pandas as pd

from app.exceptions.business import ServiceError

logger = logging.getLogger(__name__)


def normalize_timestamps(df: Any) -> pd.DataFrame:
    """
    テスト用ヘルパー: タイムスタンプを Asia/Tokyo に正規化します。

    """
    try:
        if isinstance(df.index, pd.DatetimeIndex):
            if df.index.tz is None:
                df_normalized = df.copy()
                df_normalized.index = df_normalized.index.tz_localize(
                    "Asia/Tokyo"
                )
            else:
                df_normalized = df.copy()
                df_normalized.index = df_normalized.index.tz_convert(
                    "Asia/Tokyo"
                )
            return df_normalized
        else:
            raise ServiceError(message="Index is not a DatetimeIndex")
    except Exception as e:
        logger.error(f"タイムスタンプ正規化エラー（テストヘルパー）: {e}")
        raise


def safe_float(value) -> Optional[float]:
    """
    テスト用ヘルパー: 安全な float 変換

    - NaN または None は None を返す
    - 変換失敗時は None を返す
    """
    if pd.isna(value) or value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value) -> Optional[int]:
    """
    テスト用ヘルパー: 安全な int 変換

    - NaN または None は None を返す
    - 変換失敗時は None を返す
    """
    if pd.isna(value) or value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
