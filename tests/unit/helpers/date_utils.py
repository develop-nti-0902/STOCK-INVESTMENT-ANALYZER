from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Union


def normalize_date_param(
    d: Union[date, datetime, str, None],
) -> Optional[date]:
    """
    start_date/end_date パラメータを Optional[date] に正規化します。
    - datetime -> date
    - date -> date
    - ISO 形式の文字列 -> date (失敗時は None)
    - None -> None
    """
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        try:
            return date.fromisoformat(d)
        except Exception:
            try:
                return datetime.fromisoformat(d).date()
            except Exception:
                return None
    return None
