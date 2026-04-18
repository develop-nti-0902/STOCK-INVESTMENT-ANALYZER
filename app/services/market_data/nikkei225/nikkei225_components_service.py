"""日経225構成銘柄サービス."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import aiohttp
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market_data.nikkei225 import Nikkei225ComponentRepository
from app.services.data_synchronization._core.file_managers import TempFileManagerMixin
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Nikkei225ComponentsService(TempFileManagerMixin):
    """日経225構成銘柄の取得・保存サービス."""

    OFFICIAL_URL = (
        "https://indexes.nikkei.co.jp/nkave/archives/file/"
        "nikkei_225_price_adjustment_factor_jp.csv"
    )
    ENCODING = "shift_jis"
    TIMEOUT = 30
    CSV_FILENAME = "nikkei_225_price_adjustment_factor_jp.csv"

    def __init__(self, session: AsyncSession) -> None:
        """サービスを初期化する."""
        self.session = session
        self.repository = Nikkei225ComponentRepository(session)

    async def fetch_and_update(self) -> dict[str, Any]:
        """公式CSVから日経225構成銘柄を取得してDBに保存する.

        Returns:
            dict: {"success": bool, "count": int, "error": str|None}
        """
        with self.tempdir_context(prefix="nikkei225_") as temp_dir:
            try:
                logger.info("Fetching Nikkei225 components from official source")
                timeout = aiohttp.ClientTimeout(total=self.TIMEOUT)
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(self.OFFICIAL_URL, timeout=timeout) as response:
                        response.raise_for_status()
                        csv_bytes = await response.read()
                        csv_text = csv_bytes.decode(self.ENCODING)
                csv_path = temp_dir / self.CSV_FILENAME
                csv_path.write_text(csv_text, encoding=self.ENCODING)
                logger.info("CSV downloaded to temporary file: %s", csv_path)

                df = pd.read_csv(str(csv_path), encoding=self.ENCODING)
                records = []
                for _, row in df.iterrows():
                    try:
                        records.append(
                            {
                                "stock_code": str(int(row["コード"])).zfill(4),
                                "price_adjustment_factor": float(row["株価換算係数"]),
                                "effective_date": datetime.strptime(
                                    str(row["対象日付"]), "%Y/%m/%d"
                                ).date(),
                            }
                        )
                    except (ValueError, KeyError) as e:
                        logger.warning("Row parse error: %s, row=%s", e, row)
                        continue

                if not records:
                    logger.error("No valid records found in CSV")
                    return {"success": False, "error": "No valid records found", "count": 0}

                logger.info("Parsed %d records from CSV", len(records))
                result = await self.repository.upsert_batch(records)
                await self.session.commit()
                logger.info("Successfully saved %d Nikkei225 components", len(result))
                return {"success": True, "count": len(result), "error": None}

            except aiohttp.ClientError as e:
                logger.error("Network error fetching Nikkei225 CSV: %s", e)
                return {"success": False, "error": f"Network error: {e}", "count": 0}
            except Exception as e:
                logger.exception("Unexpected error in fetch_and_update")
                return {"success": False, "error": f"Unexpected error: {e}", "count": 0}
            finally:
                logger.info("Temporary CSV file cleaned up automatically")

    async def is_in_nikkei225(self, stock_code: str) -> bool:
        """銘柄コードが日経225に含まれるか判定する."""
        component = await self.repository.find_by_code(stock_code.zfill(4))
        return component is not None
