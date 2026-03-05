"""業種（33分類）マスター Repository モジュール."""

from typing import TYPE_CHECKING, Dict, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.stock_master import Sector33Master
from app.repositories.core.base import BaseRepository

if TYPE_CHECKING:
    from app.services.screening.models import ScreeningConfig


class Sector33MasterRepository(BaseRepository[Sector33Master]):
    """業種（33分類）マスター用 Repository."""

    def __init__(self, session: AsyncSession):
        """初期化."""
        super().__init__(session, model=Sector33Master)

    async def get_by_code(self, code: str) -> Optional[Sector33Master]:
        """コードで単一レコード取得.

        Args:
            code (str): 業種コード

        Returns:
            Optional[Sector33Master]: 見つかればモデル、なければ None
        """
        result = await self.session.execute(select(self.model).where(self.model.code == code))
        return result.scalar_one_or_none()

    async def get_or_create(self, code: str, name: str) -> tuple[Sector33Master, bool]:
        """Upsert: 存在する場合は取得、ない場合は作成.

        Args:
            code (str): 業種コード
            name (str): 業種名

        Returns:
            tuple[Sector33Master, bool]: (レコード, 新規作成フラグ)
        """
        existing = await self.get_by_code(code)
        if existing:
            return existing, False

        new_record = self.model(code=code, name=name)
        self.session.add(new_record)
        await self.session.flush()
        return new_record, True

    async def list_all(self) -> list[Sector33Master]:
        """全レコード取得.

        Returns:
            list[Sector33Master]: 全レコードのリスト
        """
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())

    async def delete_all(self) -> int:
        """全レコード削除.

        Returns:
            int: 削除したレコード数
        """
        stmt = delete(self.model)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount) if result.rowcount else 0  # type: ignore[attr-defined]

    async def as_config_dict(self) -> "Dict[str, 'ScreeningConfig']":
        """業種設定を辞書形式で返す.

        DB から全レコードを取得し、ScreeningConfig に変換して辞書形式で返します。
        キーは業種コード、値は ScreeningConfig インスタンスです。

        Returns:
            Dict[str, ScreeningConfig]: 業種コードをキーとしたスクリーニング設定辞書

        Raises:
            Exception: DB読み込み失敗時
        """
        # 循環参照を避けるため、実行時にインポート
        from app.services.screening.models import ScreeningConfig

        records = await self.list_all()
        config_dict: Dict[str, ScreeningConfig] = {}

        for record in records:
            config_dict[record.code] = ScreeningConfig(
                industry_code=record.code,
                industry_name=record.name,
            )

        return config_dict


__all__ = ["Sector33MasterRepository"]
