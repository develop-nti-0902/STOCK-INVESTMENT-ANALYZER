"""JPX 銘柄マスタフェッチャー.

JPX（日本取引所グループ）から銘柄マスタデータを取得して
正規化するユーティリティを提供します。

Attributes:
    DEFAULT_URL (str): JPX のデータダウンロード URL（クラス定数）

Notes:
    実装は Excel ファイルをダウンロードし、pandas で解析、
    Pydantic モデルへ正規化します。
"""

from io import BytesIO
from typing import Any, Optional, Union

import aiohttp
import pandas as pd
from pydantic import ValidationError

from app.exceptions.business import ServiceError
from app.exceptions.external_api import JPXAPIError
from app.exceptions.validation import FieldValidationError
from app.schemas.market_data.stock_master import StockMasterNormalized, StockMasterRaw
from app.services.data_synchronization._core.fetchers.base_fetcher import BaseFetcher
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StockMasterFetcher(BaseFetcher[StockMasterNormalized]):
    """StockMasterFetcher (JPX implementation).

    JPX の銘柄一覧 Excel を取得して正規化済みの
    :class:`~app.schemas.market_data.stock_master.StockMasterNormalized` の
    リストを返します.

    Attributes:
        url (str): JPX のダウンロード URL.
    """

    DEFAULT_URL = (
        "https://www.jpx.co.jp/markets/statistics-equities/" "misc/tvdivq0000001vg2-att/data_j.xls"
    )

    def __init__(self, url: Optional[str] = None):
        """Initialize StockMasterFetcher.

        Args:
            url (Optional[str]): JPX データ URL。None の場合は
                    ``DEFAULT_URL`` が使用されます.
        """
        self.url = url or self.DEFAULT_URL

    async def fetch(self, identifier: str, **kwargs: Any) -> StockMasterNormalized:
        """Fetch a single stock master record (not supported).

        JPX は全銘柄を一括で提供するため、個別取得は未サポートです.

        Raises:
            NotImplementedError: このフェッチャーは単一取得をサポートしません。
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
        """Fetch multiple stock master records by identifiers (not supported).

        Raises:
            NotImplementedError: このフェッチャーは識別子によるバッチ取得を
            サポートしません。代わりに :meth:`fetch_all` を使用してください.
        """
        raise NotImplementedError(
            """
            StockMasterFetcher does not support batch fetch with identifiers.
            Use fetch_all() instead.
            """
        )

    async def fetch_all(self) -> list[StockMasterNormalized]:
        """Fetch and normalize all stock master records from JPX.

        Returns:
            List[StockMasterNormalized]: 正規化された銘柄マスタのリスト.

        Raises:
            JPXAPIError: ダウンロードや解析に失敗した場合に送出されます.
        """
        logger.info("Starting JPX stock master data fetch", extra={"url": self.url})

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
            ServiceError,
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

    async def fetch_and_extract_masters(self) -> dict[str, Any]:
        """JPX データ取得 + マスター値抽出.

        JPX からデータを取得し、unique な分類値（市場区分、業種、規模など）を
        抽出して、マスターテーブル作成用のデータと元データの両方を返します。

        Returns:
            dict[str, Any]: 以下のキーを含む辞書
                - "market_categories": {code: name} マッピング（市場区分）
                - "sector_33": {code: name} マッピング（業種33分類）
                - "sector_17": {code: name} マッピング（業種17分類）
                - "scale": {code: name} マッピング（規模）
                - "stocks": List[StockMasterNormalized]（正規化済み銘柄データ）

        Raises:
            JPXAPIError: ダウンロードや解析に失敗した場合.
        """
        # Step 1: raw データ取得
        raw_stocks = await self.fetch_all()

        logger.info("Extracting unique master values", extra={"total_stocks": len(raw_stocks)})

        # Step 2: unique マスター値抽出
        return {
            "market_categories": self._extract_unique_market_categories(raw_stocks),
            "sector_33": self._extract_unique_sector_33(raw_stocks),
            "sector_17": self._extract_unique_sector_17(raw_stocks),
            "scale": self._extract_unique_scale_codes(raw_stocks),
            "stocks": raw_stocks,
        }

    def _extract_unique_market_categories(
        self, data: list[StockMasterNormalized]
    ) -> dict[str, str]:
        """JPX raw データから unique な市場区分を抽出.

        Args:
            data (list[StockMasterNormalized]): 正規化済みデータ

        Returns:
            dict[str, str]: {code: name} マッピング
        """
        market_map = {}
        for stock in data:
            market_cat = stock.market_category
            if market_cat:
                # 有効値をそのまま code として使用
                market_map[market_cat] = market_cat

        logger.info("Extracted unique market categories", extra={"count": len(market_map)})
        return market_map

    def _extract_unique_sector_33(self, data: list[StockMasterNormalized]) -> dict[str, str]:
        """業種33分類を抽出（{code: name}）.

        Args:
            data (list[StockMasterNormalized]): 正規化済みデータ

        Returns:
            dict[str, str]: {コード: 業種名} マッピング
        """
        sector_map = {}
        for stock in data:
            code = stock.sector_code_33
            name = stock.sector_name_33
            if code and name:
                sector_map[code] = name

        logger.info("Extracted unique sector_33 codes", extra={"count": len(sector_map)})
        return sector_map

    def _extract_unique_sector_17(self, data: list[StockMasterNormalized]) -> dict[str, str]:
        """業種17分類を抽出（{code: name}）.

        Args:
            data (list[StockMasterNormalized]): 正規化済みデータ

        Returns:
            dict[str, str]: {コード: 業種名} マッピング
        """
        sector_map = {}
        for stock in data:
            code = stock.sector_code_17
            name = stock.sector_name_17
            if code and name:
                sector_map[code] = name

        logger.info("Extracted unique sector_17 codes", extra={"count": len(sector_map)})
        return sector_map

    def _extract_unique_scale_codes(self, data: list[StockMasterNormalized]) -> dict[str, str]:
        """規模を抽出（{code: name}）.

        Args:
            data (list[StockMasterNormalized]): 正規化済みデータ

        Returns:
            dict[str, str]: {コード: 規模区分名} マッピング
        """
        scale_map = {}
        for stock in data:
            code = stock.scale_code
            category = stock.scale_category
            if code and category:
                scale_map[code] = category

        logger.info("Extracted unique scale codes", extra={"count": len(scale_map)})
        return scale_map

    async def _download_excel(self) -> bytes:
        """Download the Excel file from JPX.

        Returns:
            bytes: Excel ファイルのバイナリデータ.

        Raises:
            aiohttp.ClientError: HTTP 通信エラーが発生した場合.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                response.raise_for_status()
                return await response.read()

    async def _parse_excel(self, excel_data: bytes) -> pd.DataFrame:
        """Parse Excel binary into a :class:`pandas.DataFrame`.

        Args:
            excel_data (bytes): ダウンロード済みの Excel バイト列.

        Returns:
            pd.DataFrame: 解析結果の DataFrame.

        Raises:
            ValueError: 解析に失敗した場合.
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
            raise ServiceError(message=f"Failed to parse Excel file: {str(e)}") from e

    async def _normalize_data(self, df: pd.DataFrame) -> list[StockMasterNormalized]:
        """Normalize DataFrame rows into Pydantic models.

        Args:
            df (pd.DataFrame): 解析済みの DataFrame.

        Returns:
            List[StockMasterNormalized]: 正規化されたレコードのリスト.

        Raises:
            ValueError: 全行のバリデーションに失敗した場合.
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
                        str(raw_data.scale_code) if raw_data.scale_code is not None else None
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
                FieldValidationError,
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
                raise ServiceError(message="All rows failed validation. Check data format.")

        return normalized_data

    def _normalize_stock_code(self, code: Optional[Union[str, int]]) -> str:
        """銘柄コードを文字列に正規化して返す.

        Args:
            code: 生の銘柄コード値

        Returns:
            正規化された銘柄コード文字列

        Raises:
            FieldValidationError: 無効なコードや空文字の場合
        """
        if not code and code != 0:
            raise FieldValidationError(message="Stock code is required")

        normalized = str(code).strip()

        if not normalized:
            raise FieldValidationError(message="Stock code cannot be empty")

        return normalized

    def _normalize_stock_name(self, name: Optional[str]) -> str:
        """銘柄名を正規化して非空文字列を返す.

        Args:
            name: 生の銘柄名

        Returns:
            正規化された銘柄名

        Raises:
            FieldValidationError: 無効または空文字列の場合
        """
        if not name:
            raise FieldValidationError(message="Stock name is required")

        normalized = str(name).strip()

        if not normalized:
            raise FieldValidationError(message="Stock name cannot be empty")

        return normalized

    def _normalize_date(self, date: Optional[Union[str, int]]) -> Optional[str]:
        """日付に類する値を可能な限り YYYYMMDD 形式の文字列に正規化する.

        Args:
            date: 生の日付値（例: '2020/1/2', '2020-01-02', 20200102）

        Returns:
            正規化された文字列、解析できない場合は None
        """
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
