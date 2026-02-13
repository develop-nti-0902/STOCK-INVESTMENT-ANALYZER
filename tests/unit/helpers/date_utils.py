"""Date utilities for tests."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Union


def normalize_date_param(
    d: Union[date, datetime, str, None],
) -> Optional[date]:
    """Normalize start_date/end_date parameters to Optional[date]."""
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
