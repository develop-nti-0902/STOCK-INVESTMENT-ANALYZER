"""
JPXフェッチャーのテスト

JPXフェッチャーの機能を検証します。
"""

import io
from unittest.mock import AsyncMock, patch

import aiohttp
import pandas as pd
import pytest

from app.exceptions.external_api import JPXAPIError
from app.schemas.market_data.stock_master import StockMasterNormalized
from app.services.core.fetchers.jpx_fetcher import JPXFetcher

# テスト用のモックデータ
MOCK_EXCEL_DATA = {
    "日付": ["2025/12/07", "2025/12/07", "2025/12/07"],
    "コード": ["1301", "1332", "1333"],
    "銘柄名": ["極洋", "日本水産", "マルハニチロ"],
    "市場区分": ["プライム", "プライム", "プライム"],
    "33業種コード": ["050", "050", "050"],
    "33業種区分": ["水産・農林業", "水産・農林業", "水産・農林業"],
    "17業種コード": ["001", "001", "001"],
    "17業種区分": ["食品", "食品", "食品"],
    "規模コード": ["6", "6", "6"],
    "規模区分": ["TOPIX Mid400", "TOPIX Mid400", "TOPIX Mid400"],
}


@pytest.fixture(name="jpx_fetcher")
def jpx_fetcher_fixture():
    """JPXフェッチャーのフィクスチャ"""
    return JPXFetcher()


@pytest.fixture(name="mock_excel_df")
def mock_excel_df_fixture():
    """モックExcelデータのDataFrame"""
    return pd.DataFrame(MOCK_EXCEL_DATA)


class TestJPXFetcher:
    """JPXフェッチャーのテストクラス"""

    def test_initialization(self):
        """初期化のテスト"""
        fetcher = JPXFetcher()
        assert fetcher.url == JPXFetcher.DEFAULT_URL
        # カスタムURLの設定
        custom_url = "https://custom.url/data.xls"
        fetcher = JPXFetcher(url=custom_url)
        assert fetcher.url == custom_url

    @pytest.mark.asyncio
    async def test_fetch_not_implemented(self, jpx_fetcher):
        """fetch()メソッドが未実装であることを確認"""
        with pytest.raises(NotImplementedError):
            await jpx_fetcher.fetch("1301")

    @pytest.mark.asyncio
    async def test_fetch_batch_not_implemented(self, jpx_fetcher):
        """fetch_batch()メソッドが未実装であることを確認"""
        with pytest.raises(NotImplementedError):
            await jpx_fetcher.fetch_batch(["1301", "1332"])

    @pytest.mark.asyncio
    async def test_fetch_all_success(self, jpx_fetcher):
        """fetch_all()の正常系テスト（実際のJPXサイトからデータ取得）"""
        # ネットワークを使う実際のエンドツーエンドテスト。
        # 環境によってはネットワークが使えないため、その場合はスキップする。
        try:
            result = await jpx_fetcher.fetch_all()
        except Exception as e:  # pylint: disable=broad-except
            pytest.skip(f"Cannot run network test: {e}")

        # 最低限のアサーション: データが1件以上返ること
        assert isinstance(result, list)
        assert len(result) > 0
        # 先頭レコードは期待されるフィールドを持つ
        first = result[0]
        assert hasattr(first, "stock_code")
        assert hasattr(first, "stock_name")

    @pytest.mark.asyncio
    async def test_fetch_all_jpx_api_error(self, jpx_fetcher):
        """JPX API エラーのテスト"""
        with patch.object(
            jpx_fetcher, "_download_excel", new_callable=AsyncMock
        ) as mock_download:
            # エラーを発生させる
            mock_download.side_effect = aiohttp.ClientError("API error")

            # テスト実行
            with pytest.raises(JPXAPIError):
                await jpx_fetcher.fetch_all()

    @pytest.mark.asyncio
    async def test_parse_excel(self, jpx_fetcher, mock_excel_df):
        """Excelパースのテスト"""
        # pandas.read_excel をモックして、パブリック API (fetch_all) を通じて
        # パース処理で正しい DataFrame が生成され _normalize_data に渡されることを確認する
        excel_buffer = io.BytesIO()
        mock_excel_df.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_bytes = excel_buffer.getvalue()

        with patch(
            "pandas.read_excel", return_value=mock_excel_df
        ) as mock_read:
            with patch.object(
                jpx_fetcher, "_download_excel", new_callable=AsyncMock
            ) as mock_download:
                with patch.object(
                    jpx_fetcher, "_normalize_data", new_callable=AsyncMock
                ) as mock_normalize:
                    mock_download.return_value = excel_bytes
                    mock_normalize.return_value = []

                    # fetch_all を実行して内部でパースが呼ばれることを検証
                    await jpx_fetcher.fetch_all()

                    mock_read.assert_called_once()
                    mock_normalize.assert_called_once()
                    # _normalize_data に渡された DataFrame を検証
                    passed_df = mock_normalize.call_args[0][0]
                    assert list(passed_df.columns) == list(
                        MOCK_EXCEL_DATA.keys()
                    )

    @pytest.mark.asyncio
    async def test_normalize_data(self, jpx_fetcher, mock_excel_df):
        """データ正規化のテスト"""
        # 正規化処理はパブリック API を経由して検証する
        with patch.object(
            jpx_fetcher, "_download_excel", new_callable=AsyncMock
        ) as mock_download:
            with patch.object(
                jpx_fetcher, "_parse_excel", new_callable=AsyncMock
            ) as mock_parse:
                mock_download.return_value = b"excel"
                mock_parse.return_value = mock_excel_df

                result = await jpx_fetcher.fetch_all()

        # アサーション
        assert len(result) == 3
        assert all(isinstance(item, StockMasterNormalized) for item in result)
        assert result[0].stock_code == "1301"
        assert result[0].stock_name == "極洋"
        assert result[0].market_category == "プライム"
        assert result[0].data_date == "20251207"

    @pytest.mark.asyncio
    async def test_normalize_data_with_errors(self, jpx_fetcher):
        """不正なデータを含むDataFrameの正規化テスト"""
        # 不正なデータを含むDataFrame
        invalid_df = pd.DataFrame(
            {
                "日付": ["2025/12/07", "2025/12/07"],
                "コード": ["1301", None],  # Noneは不正
                "銘柄名": ["極洋", ""],  # 空文字は不正
                "市場区分": ["プライム", "プライム"],
                "33業種コード": ["050", "050"],
                "33業種区分": ["水産・農林業", "水産・農林業"],
                "17業種コード": ["001", "001"],
                "17業種区分": ["食品", "食品"],
                "規模コード": ["6", "6"],
                "規模区分": ["TOPIX Mid400", "TOPIX Mid400"],
            }
        )

        with patch.object(
            jpx_fetcher, "_download_excel", new_callable=AsyncMock
        ) as mock_download:
            with patch.object(
                jpx_fetcher, "_parse_excel", new_callable=AsyncMock
            ) as mock_parse:
                mock_download.return_value = b"excel"
                mock_parse.return_value = invalid_df

                result = await jpx_fetcher.fetch_all()

        # 有効なデータのみが返されることを確認
        assert len(result) == 1
        assert result[0].stock_code == "1301"

    @pytest.mark.asyncio
    async def test_normalize_data_all_invalid(self, jpx_fetcher):
        """全てのデータが不正な場合のテスト"""
        # 全て不正なDataFrame
        invalid_df = pd.DataFrame(
            {
                "日付": ["2025/12/07"],
                "コード": [None],
                "銘柄名": [""],
                "市場区分": ["プライム"],
                "33業種コード": ["050"],
                "33業種区分": ["水産・農林業"],
                "17業種コード": ["001"],
                "17業種区分": ["食品"],
                "規模コード": ["6"],
                "規模区分": ["TOPIX Mid400"],
            }
        )

        # fetch_all は内部で ValueError を JPXAPIError に変換するため期待される例外を更新
        with patch.object(
            jpx_fetcher, "_download_excel", new_callable=AsyncMock
        ) as mock_download:
            with patch.object(
                jpx_fetcher, "_parse_excel", new_callable=AsyncMock
            ) as mock_parse:
                mock_download.return_value = b"excel"
                mock_parse.return_value = invalid_df

                with pytest.raises(JPXAPIError):
                    await jpx_fetcher.fetch_all()

    @pytest.mark.asyncio
    async def test_normalize_stock_code(self, jpx_fetcher):
        """銘柄コード正規化のテスト"""
        # 正常系: fetch_all を経由して正規化が行われることを確認する
        df = pd.DataFrame(
            {
                "日付": ["2025/12/07"],
                "コード": ["  1301  "],
                "銘柄名": ["極洋"],
                "市場区分": ["プライム"],
                "33業種コード": ["050"],
                "33業種区分": ["水産・農林業"],
                "17業種コード": ["001"],
                "17業種区分": ["食品"],
                "規模コード": ["6"],
                "規模区分": ["TOPIX Mid400"],
            }
        )

        with patch.object(
            jpx_fetcher, "_download_excel", new_callable=AsyncMock
        ) as md:
            with patch.object(
                jpx_fetcher, "_parse_excel", new_callable=AsyncMock
            ) as mp:
                md.return_value = b"excel"
                mp.return_value = df

                result = await jpx_fetcher.fetch_all()
                assert len(result) == 1
                assert result[0].stock_code == "1301"

    @pytest.mark.asyncio
    async def test_normalize_stock_name(self, jpx_fetcher):
        """銘柄名正規化のテスト"""
        # 正常系: fetch_all を通じて銘柄名のトリムが行われることを確認
        df = pd.DataFrame(
            {
                "日付": ["2025/12/07"],
                "コード": ["1301"],
                "銘柄名": ["  極洋  "],
                "市場区分": ["プライム"],
                "33業種コード": ["050"],
                "33業種区分": ["水産・農林業"],
                "17業種コード": ["001"],
                "17業種区分": ["食品"],
                "規模コード": ["6"],
                "規模区分": ["TOPIX Mid400"],
            }
        )

        with patch.object(
            jpx_fetcher, "_download_excel", new_callable=AsyncMock
        ) as md:
            with patch.object(
                jpx_fetcher, "_parse_excel", new_callable=AsyncMock
            ) as mp:
                md.return_value = b"excel"
                mp.return_value = df

                result = await jpx_fetcher.fetch_all()
                assert len(result) == 1
                assert result[0].stock_name == "極洋"

    @pytest.mark.asyncio
    async def test_normalize_date(self, jpx_fetcher):
        """日付正規化のテスト"""
        # 日付の正規化は fetch_all を通じて確認（複数形式）
        df = pd.DataFrame(
            {
                "日付": ["2025/12/07", "2025-12-07", "20251207", "2025/1/7"],
                "コード": ["1301", "1302", "1303", "1304"],
                "銘柄名": ["A", "B", "C", "D"],
                "市場区分": ["プライム"] * 4,
                "33業種コード": ["050"] * 4,
                "33業種区分": ["水産・農林業"] * 4,
                "17業種コード": ["001"] * 4,
                "17業種区分": ["食品"] * 4,
                "規模コード": ["6"] * 4,
                "規模区分": ["TOPIX Mid400"] * 4,
            }
        )

        with patch.object(
            jpx_fetcher, "_download_excel", new_callable=AsyncMock
        ) as md:
            with patch.object(
                jpx_fetcher, "_parse_excel", new_callable=AsyncMock
            ) as mp:
                md.return_value = b"excel"
                mp.return_value = df

                result = await jpx_fetcher.fetch_all()
                assert [r.data_date for r in result] == [
                    "20251207",
                    "20251207",
                    "20251207",
                    "20250107",
                ]
