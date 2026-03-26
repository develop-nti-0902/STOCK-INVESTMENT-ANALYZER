"""日経225日足データ Pydantic スキーマ."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Nikkei2251dCreate(BaseModel):
    """DB 挿入用スキーマ."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    adj_close: Optional[float] = None
    volume: int = 0


class Nikkei2251dRead(Nikkei2251dCreate):
    """DB 読み出し用スキーマ."""

    id: int
    created_at: datetime
    updated_at: datetime
