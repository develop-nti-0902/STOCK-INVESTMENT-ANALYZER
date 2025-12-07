from typing import List, Optional, Type

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_master import StockMaster
from app.repositories.base import BaseRepository


class StockMasterRepository(BaseRepository[StockMaster]):
    """
    StockMaster専用のRepository

    - 一括UPSERTを提供します（PostgreSQLのON CONFLICTを利用）
    """

    def __init__(
        self,
        model: Type[StockMaster] = StockMaster,
        session: Optional[AsyncSession] = None,
    ):
        # BaseRepository は非 None の AsyncSession を想定しているため、
        # 静的解析器向けに型チェック無視を残しています
        kwargs = {"model": model, "session": session}
        super().__init__(**kwargs)  # type: ignore[arg-type]

    async def bulk_upsert(self, records: List[dict]) -> int:
        """
        一括UPSERT（重複時は更新）

        Args:
            records: レコード辞書のリスト

        Returns:
            int: 処理したレコード数（成功したと仮定して入力件数を返却）
        """
        if not records:
            return 0

        table = self.model.__table__

        insert_stmt = pg_insert(table).values(records)

        # 更新対象カラム: id以外の全カラムを除外値で更新する
        update_dict = {
            c.name: getattr(insert_stmt.excluded, c.name)
            for c in table.c
            if c.name != "id"
        }

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["stock_code"], set_=update_dict
        )

        await self.session.execute(stmt)
        # flushしてDB側に反映（get_db()がcommitを担当）
        await self.session.flush()

        # SQLAlchemyの非同期結果から正確な件数取得は環境依存のため
        # 入力件数を返す。呼び出し側で差分確認する場合は別実装。
        return len(records)


__all__ = ["StockMasterRepository"]
