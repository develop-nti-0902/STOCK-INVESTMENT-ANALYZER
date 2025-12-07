"""
JPX銘柄マスタフェッチャー

JPX（日本取引所グループ）から銘柄マスタデータを取得します。
仕様書: docs/architecture/layers/service_layer.md 3.2.2章
Issue: #68
"""

from io import BytesIO
from typing import Any, Optional

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


class JPXFetcher(BaseFetcher[StockMasterNormalized]):
    """
    JPX銘柄マスタフェッチャー

    JPXの銘柄一覧エクセルファイルをダウンロードし、
    銘柄マスタデータを取得・正規化します。

    Attributes:
        url: JPXのデータダウンロードURL
        timeout: タイムアウト時間（秒）
        max_retries: 最大リトライ回数
        retry_delay: リトライ待機時間（秒）
    """

    DEFAULT_URL = (
        "https://www.jpx.co.jp/markets/statistics-equities/"
        "misc/tvdivq0000001vg2-att/data_j.xls"
    )
    # シンプル化: タイムアウトやリトライは行わない

    def __init__(self, url: Optional[str] = None):
        """
        Args:
            url: JPXデータURL（Noneの場合デフォルトURL使用）
            (シンプル化) タイムアウト・リトライは行わない
        """
        self.url = url or self.DEFAULT_URL

    async def fetch(
        self, identifier: str, **kwargs: Any
    ) -> StockMasterNormalized:
        """
        単一銘柄の取得（このフェッチャーでは未使用）

        JPXからは全銘柄を一括取得するため、このメソッドは使用しません。
        fetch_batch()を使用してください。

        Raises:
            NotImplementedError: 常に発生
        """
        raise NotImplementedError(
            "JPXFetcher does not support single fetch. Use fetch_batch() "
            "or fetch_all() instead."
        )

    async def fetch_batch(
        self, identifiers: list[str], **kwargs: Any
    ) -> list[StockMasterNormalized]:
        """
        複数銘柄の取得（このフェッチャーでは未使用）

        JPXからは全銘柄を一括取得するため、このメソッドは使用しません。
        fetch_all()を使用してください。

        Raises:
            NotImplementedError: 常に発生
        """
        raise NotImplementedError(
            "JPXFetcher does not support batch fetch with identifiers. "
            "Use fetch_all() instead."
        )

    async def fetch_all(self) -> list[StockMasterNormalized]:
        """
        全銘柄マスタデータを取得

        JPXからエクセルファイルをダウンロードし、全銘柄のマスタデータを
        正規化して返します。

        Returns:
            list[StockMasterNormalized]: 正規化された銘柄マスタデータのリスト

        Raises:
            JPXAPIError: データ取得に失敗した場合
            APITimeoutError: タイムアウトした場合
        """
        logger.info(
            "Starting JPX stock master data fetch", extra={"url": self.url}
        )

        try:
            # エクセルファイルをダウンロード（1回のみ）
            excel_data = await self._download_excel()

            # DataFrameに変換
            df = await self._parse_excel(excel_data)

            # 正規化して返却
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

        Raises:
            aiohttp.ClientError: ダウンロードに失敗した場合
        """
        # シンプル化: セッションに明示的なタイムアウトを与えずに1回だけ取得を試みる
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                response.raise_for_status()
                return await response.read()

    async def _parse_excel(self, excel_data: bytes) -> pd.DataFrame:
        """
        エクセルファイルをDataFrameに変換

        Args:
            excel_data: エクセルファイルのバイトデータ

        Returns:
            pd.DataFrame: 変換されたDataFrame

        Raises:
            ValueError: パースに失敗した場合
        """
        try:
            # BytesIOに変換してpandasで読み込み
            # xlrdライブラリを使用（.xlsファイル対応）
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

        Args:
            df: パースされたDataFrame

        Returns:
            list[StockMasterNormalized]: 正規化された銘柄マスタデータ

        Raises:
            ValueError: 正規化に失敗した場合
        """
        normalized_data = []
        errors = []

        for idx, row in df.iterrows():
            try:
                # まず生データとしてパース（aliasを使用）
                raw_data = StockMasterRaw.model_validate(
                    row.to_dict(), from_attributes=True
                )

                # 正規化されたデータに変換
                normalized = StockMasterNormalized(
                    stock_code=self._normalize_stock_code(raw_data.code),
                    stock_name=self._normalize_stock_name(raw_data.name),
                    market_category=raw_data.market,
                    sector_code_33=raw_data.sector_code_33,
                    sector_name_33=raw_data.sector_name_33,
                    sector_code_17=raw_data.sector_code_17,
                    sector_name_17=raw_data.sector_name_17,
                    scale_code=raw_data.scale_code,
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

        # エラーがあればログ出力（全てエラーの場合は例外を投げる）
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

    def _normalize_stock_code(self, code: Optional[str]) -> str:
        """
        銘柄コードを正規化

        Args:
            code: 銘柄コード

        Returns:
            str: 正規化された銘柄コード

        Raises:
            ValueError: コードが不正な場合
        """
        if not code:
            raise ValueError("Stock code is required")

        # 文字列に変換して前後の空白を除去
        normalized = str(code).strip()

        if not normalized:
            raise ValueError("Stock code cannot be empty")

        return normalized

    def _normalize_stock_name(self, name: Optional[str]) -> str:
        """
        銘柄名を正規化

        Args:
            name: 銘柄名

        Returns:
            str: 正規化された銘柄名

        Raises:
            ValueError: 銘柄名が不正な場合
        """
        if not name:
            raise ValueError("Stock name is required")

        # 文字列に変換して前後の空白を除去
        normalized = str(name).strip()

        if not normalized:
            raise ValueError("Stock name cannot be empty")

        return normalized

    def _normalize_date(self, date: Optional[str]) -> Optional[str]:
        """
        日付を正規化（YYYYMMDD形式）

        Args:
            date: 日付文字列

        Returns:
            Optional[str]: 正規化された日付（YYYYMMDD形式）
        """
        if not date:
            return None

        # 文字列に変換して前後の空白を除去
        normalized = str(date).strip()

        # 空の場合はNoneを返す
        if not normalized:
            return None

        # YYYY/MM/DD形式の場合はYYYYMMDDに変換
        if "/" in normalized:
            parts = normalized.split("/")
            if len(parts) == 3:
                return f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"

        # YYYY-MM-DD形式の場合はYYYYMMDDに変換
        if "-" in normalized:
            parts = normalized.split("-")
            if len(parts) == 3:
                return f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"

        # すでにYYYYMMDD形式の場合はそのまま返す
        return normalized


__all__ = ["JPXFetcher"]
