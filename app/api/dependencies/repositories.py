"""
Repository依存性注入プロバイダ

FastAPIのDependsパターンを使用して、各Repositoryインスタンスを提供する。
共通モジュール（app.utils.database）のget_db()を使用してDBセッションを取得する。

仕様書: docs/architecture/layers/data_access_layer.md 3.3章
"""

from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.utils.database import get_db


def get_base_repository(
    db: AsyncSession = Depends(get_db),
) -> BaseRepository[Any]:
    """
    BaseRepositoryを提供（汎用CRUD操作用）

    使用例:
        ```python
        from fastapi import APIRouter, Depends
        from app.api.dependencies.repositories import get_base_repository
        from app.repositories.base import BaseRepository

        router = APIRouter()

        @router.get("/items/{item_id}")
        async def get_item(
            item_id: int,
            repo: BaseRepository = Depends(get_base_repository)
        ):
            item = await repo.get_by_id(item_id)
            return item
        ```

    Args:
        db: 非同期DBセッション（共通モジュールから提供）

    Returns:
        BaseRepository: 汎用CRUD操作Repository

    Note:
        - 実際のプロジェクトでは、このプロバイダは直接使用せず、
          各エンティティ専用のRepositoryプロバイダ（例: get_stock_repository）を使用することを推奨
        - このプロバイダはテストや一時的な用途に使用
    """
    # 注意: BaseRepositoryはABCなので、実際には具象クラスを使用する必要がある
    # ここではプレースホルダとして汎用的なリポジトリを返します。
    # 実運用では特定モデル向けの具象Repository（例: StockRepository）を使用してください。
    return BaseRepository(session=db)  # type: ignore


def get_stock_master_repository(
    db: AsyncSession = Depends(get_db),
) -> BaseRepository[Any]:
    """StockMasterRepository を提供する DI プロバイダ

    遅延インポートにより循環依存を回避します。
    """
    # 遅延インポートにより循環依存を回避します。
    # pylint: disable=import-outside-toplevel
    from app.repositories.stock_master_repository import StockMasterRepository

    return StockMasterRepository(session=db)


# 以下は、各エンティティ専用のRepositoryプロバイダの例
# 実際のモデルとRepositoryクラスが実装された後に追加する

# def get_stock_repository(
#     db: AsyncSession = Depends(get_db)
# ) -> StockRepository:
#     """
#     StockRepositoryを提供（株価データ専用）
#
#     Args:
#         db: 非同期DBセッション（共通モジュールから提供）
#
#     Returns:
#         StockRepository: 株価データRepository
#     """
#     from app.repositories.stock import StockRepository
#     from app.models.stock_data import Stocks1d
#     return StockRepository(model=Stocks1d, session=db)


# def get_master_repository(
#     db: AsyncSession = Depends(get_db)
# ) -> MasterRepository:
#     """
#     MasterRepositoryを提供（銘柄マスタ専用）
#
#     Args:
#         db: 非同期DBセッション（共通モジュールから提供）
#
#     Returns:
#         MasterRepository: 銘柄マスタRepository
#     """
#     from app.repositories.master import MasterRepository
#     from app.models.stock_master import StockMaster
#     return MasterRepository(model=StockMaster, session=db)


# 将来的に追加されるRepositoryプロバイダのプレースホルダ:
# - get_fundamental_repository: ファンダメンタルデータRepository
# - get_user_repository: ユーザー管理Repository
# - get_portfolio_repository: ポートフォリオRepository
# - get_indices_repository: 市場インデックスRepository
# - get_screening_repository: スクリーニングRepository
# - get_backtest_repository: バックテストRepository
# - get_notification_repository: 通知Repository
