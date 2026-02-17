"""最新株価ビューのリフレッシュを扱うサービスモジュール.

`latest_stocks_1d` マテリアライズドビューの更新ジョブ作成と実行を提供します.
"""

from __future__ import annotations

from app.exceptions.business import ServiceError
from app.services.views.base import BaseViewService


class LatestStocksRefreshService(BaseViewService):
    """`latest_stocks_1d` ビューの同期リフレッシュサービス。

    バッチ管理（ジョブ作成・ステータス管理）を廃止し、呼び出し元で同期的に
    `run_refresh()` を実行する設計に変更しました。
    """

    def __init__(self, engine: object | None = None):
        super().__init__()
        self._engine = engine

    async def run_refresh(self) -> None:
        """`latest_stocks_1d` ビューのリフレッシュ処理を実行します。

        SQLite 環境ではマテリアライズドビューの REFRESH が無い場合があるため
        実質的に no-op になることがありますが、例外発生時は ServiceError を投げます。
        """
        try:
            self.logger.info("latest_stocks_1d is a VIEW; no DB refresh required")
            return None
        except Exception as e:
            self.logger.exception("Unexpected error in run_refresh: %s", e)
            raise ServiceError(message=f"failed to refresh latest_stocks_1d: {e}")


__all__ = ["LatestStocksRefreshService"]
