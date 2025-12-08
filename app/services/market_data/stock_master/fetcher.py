"""
JPX銘柄マスタフェッチャー

JPX（日本取引所グループ）から銘柄マスタデータを取得します。
仕様書: docs/architecture/layers/service_layer.md 3.2.2章
Issue: #68
"""

from io import BytesIO
from typing import Any, Optional, Union

import aiohttp
import pandas as pd
from pydantic import ValidationError

from app.exceptions.external_api import JPXAPIError
from app.schemas.market_data.stock_master import (
    StockMasterNormalized,
    StockMasterRaw,
)
from app.services.core.fetchers.base_fetcher import BaseFetcher
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StockMasterFetcher(BaseFetcher[StockMasterNormalized]):
    """
    銘柄マスタフェッチャー（JPX用実装）

    JPXの銘柄一覧エクセルファイルをダウンロードし、
    銘柄マスタデータを取得・正規化します。Market Data ドメイン側の
    `StockMasterFetcher` として実装します。

    Attributes:
        url: JPXのデータダウンロードURL
    """

    DEFAULT_URL = (
        "https://www.jpx.co.jp/markets/statistics-equities/"
        "misc/tvdivq0000001vg2-att/data_j.xls"
    )

    def __init__(self, url: Optional[str] = None):
        """
        Args:
            url: JPXデータURL（Noneの場合デフォルトURL使用）
        """
        self.url = url or self.DEFAULT_URL

    async def fetch(
        self, identifier: str, **kwargs: Any
    ) -> StockMasterNormalized:
        """
        単一銘柄の取得（JPXでは未サポート）

        JPXからは全銘柄を一括取得するため、このメソッドは未実装です。
        """
        raise NotImplementedError(
            """
            StockMasterFetcher does not support single fetch.
            Use fetch_all() instead.
            """
        )

    async def fetch_batch(
        self, identifiers: list[str], **kwargs: Any
    ) -> list[StockMasterNormalized]:
        """
        複数銘柄の取得（JPXでは未サポート）

        JPXからは全銘柄を一括取得するため、このメソッドは未実装です。
        """
        raise NotImplementedError(
            """
            StockMasterFetcher does not support batch fetch with identifiers.
            Use fetch_all() instead.
            """
        )

    async def fetch_all(self) -> list[StockMasterNormalized]:
        """
        全銘柄マスタデータを取得

        JPXからエクセルファイルをダウンロードし、全銘柄のマスタデータを
        正規化して返します。
        """
        logger.info(
            "Starting JPX stock master data fetch", extra={"url": self.url}
        )

        try:
            excel_data = await self._download_excel()
            df = await self._parse_excel(excel_data)
            normalized_data = await self._normalize_data(df)

            logger.info(
                "Successfully fetched JPX stock master data",
                extra={"total_count": len(normalized_data)},
            )

            return normalized_data

        except (
            aiohttp.ClientError,
            ValueError,
            pd.errors.EmptyDataError,
        ) as e:
            logger.error(
                "Failed to fetch JPX data",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            raise JPXAPIError(
                message=f"Failed to fetch JPX data: {str(e)}",
                context={"original_error": e},
            ) from e

    async def _download_excel(self) -> bytes:
        """
        JPXからエクセルファイルをダウンロード

        Returns:
            bytes: エクセルファイルのバイトデータ
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                response.raise_for_status()
                return await response.read()

    async def _parse_excel(self, excel_data: bytes) -> pd.DataFrame:
        """
        エクセルファイルをDataFrameに変換
        """
        try:
            df = pd.read_excel(BytesIO(excel_data), engine="xlrd")

            logger.info(
                "Parsed Excel file",
                extra={"rows": len(df), "columns": list(df.columns)},
            )

            return df

        except (
            ValueError,
            OSError,
            pd.errors.EmptyDataError,
        ) as e:
            raise ValueError(f"Failed to parse Excel file: {str(e)}") from e

    async def _normalize_data(
        self, df: pd.DataFrame
    ) -> list[StockMasterNormalized]:
        """
        DataFrameを正規化されたPydanticモデルに変換
        """
        normalized_data = []
        errors = []

        for idx, row in df.iterrows():
            try:
                raw_data = StockMasterRaw.model_validate(row.to_dict())

                normalized = StockMasterNormalized(
                    stock_code=self._normalize_stock_code(raw_data.code),
                    stock_name=self._normalize_stock_name(raw_data.name),
                    market_category=raw_data.market,
                    sector_code_33=(
                        str(raw_data.sector_code_33)
                        if raw_data.sector_code_33 is not None
                        else None
                    ),
                    sector_name_33=raw_data.sector_name_33,
                    sector_code_17=(
                        str(raw_data.sector_code_17)
                        if raw_data.sector_code_17 is not None
                        else None
                    ),
                    sector_name_17=raw_data.sector_name_17,
                    scale_code=(
                        str(raw_data.scale_code)
                        if raw_data.scale_code is not None
                        else None
                    ),
                    scale_category=raw_data.scale_category,
                    data_date=self._normalize_date(raw_data.date),
                    is_active=1,
                )

                normalized_data.append(normalized)

            except ValidationError as e:
                errors.append(
                    {
                        "row": idx,
                        "error": str(e),
                        "data": row.to_dict(),
                    }
                )
                logger.warning(
                    "Validation error at row %s",
                    idx,
                    extra={"error": str(e), "row_data": row.to_dict()},
                )

            except (
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
            ) as e:
                errors.append(
                    {
                        "row": idx,
                        "error": str(e),
                        "data": row.to_dict(),
                    }
                )
                logger.error(
                    "Unexpected error at row %s",
                    idx,
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "row_data": row.to_dict(),
                    },
                )

        if errors:
            logger.warning(
                "Encountered %d errors during normalization",
                len(errors),
                extra={"error_count": len(errors), "total_rows": len(df)},
            )

            if len(errors) == len(df):
                raise ValueError(
                    "All rows failed validation. Check data format."
                )

        return normalized_data

    def _normalize_stock_code(self, code: Optional[Union[str, int]]) -> str:
        if not code and code != 0:
            raise ValueError("Stock code is required")

        normalized = str(code).strip()

        if not normalized:
            raise ValueError("Stock code cannot be empty")

        return normalized

    def _normalize_stock_name(self, name: Optional[str]) -> str:
        if not name:
            raise ValueError("Stock name is required")

        normalized = str(name).strip()

        if not normalized:
            raise ValueError("Stock name cannot be empty")

        return normalized

    def _normalize_date(
        self, date: Optional[Union[str, int]]
    ) -> Optional[str]:
        if not date and date != 0:
            return None

        normalized = str(date).strip()

        if not normalized:
            return None

        if "/" in normalized:
            parts = normalized.split("/")
            if len(parts) == 3:
                return f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"

        if "-" in normalized:
            parts = normalized.split("-")
            if len(parts) == 3:
                return f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"

        return normalized


__all__ = ["StockMasterFetcher"]
