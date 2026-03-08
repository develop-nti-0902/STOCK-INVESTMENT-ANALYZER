"""配当利回り履歴生成サービスモジュール。"""

from .service import (
    DividendYieldHistoryRecord,
    DividendYieldHistoryResult,
    DividendYieldHistoryService,
)

__all__ = [
    "DividendYieldHistoryService",
    "DividendYieldHistoryRecord",
    "DividendYieldHistoryResult",
]
