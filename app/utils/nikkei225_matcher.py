"""日経225マッチャー."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.market_data.nikkei225 import Nikkei225ComponentsService


class Nikkei225Matcher:
    """Yahoo Finance ティッカーから日経225構成銘柄かを判定するクラス."""

    def __init__(self, session: AsyncSession) -> None:
        """マッチャーを初期化する."""
        self.service = Nikkei225ComponentsService(session)

    @staticmethod
    def yahoo_ticker_to_code(yahoo_ticker: str) -> str:
        """Yahoo Finance ティッカー（例: 7203.T）を4桁銘柄コードに変換する."""
        return yahoo_ticker.split(".")[0]

    async def is_nikkei225(self, yahoo_ticker: str) -> bool:
        """Yahoo Finance ティッカーが日経225構成銘柄かを判定する."""
        code = self.yahoo_ticker_to_code(yahoo_ticker)
        return await self.service.is_in_nikkei225(code)
