"""Repository依存性注入プロバイダ.

FastAPIの`Depends`パターンを使って各Repositoryインスタンスを提供します。
DBセッションは`app.utils.database.get_db()`から取得します。

仕様書: docs/architecture/layers/data_access_layer.md 3.3章
"""

from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.core.base import BaseRepository
from app.utils.database import get_db


def get_base_repository(
    db: AsyncSession = Depends(get_db),
) -> BaseRepository[Any]:
    """
    BaseRepository を提供する依存性プロバイダ.

    汎用的な CRUD 操作用の `BaseRepository` インスタンスを返します。

    Args:
        db (AsyncSession): 非同期DBセッション（`get_db` から提供される）

    Returns:
        BaseRepository[Any]: 汎用CRUD操作Repository（テスト・一時利用向け）

    Note:
        BaseRepository は抽象的なインターフェースのため、実運用では具象Repositoryを使用してください。
    """
    # 注意: BaseRepositoryはABCなので、実際には具象クラスを使用する必要がある
    # ここではプレースホルダとして汎用的なリポジトリを返します。
    # 実運用では特定モデル向けの具象Repository（例: StockRepository）を使用してください。
    return BaseRepository(session=db)


def get_stock_master_repository(
    db: AsyncSession = Depends(get_db),
) -> BaseRepository[Any]:
    """StockMasterRepository を提供する依存性プロバイダ.

    遅延インポートで循環依存を回避して `StockMasterRepository` を生成します。

    Args:
        db (AsyncSession): 非同期DBセッション

    Returns:
        BaseRepository[Any]: `StockMasterRepository` のインスタンス
    """
    # pylint: disable=import-outside-toplevel
    from app.repositories.market_data.stock_master import StockMasterRepository

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
#     from app.models.market_data.stock_price import Stocks1d
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
