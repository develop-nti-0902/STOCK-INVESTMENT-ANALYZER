"""Views 配下のサービス共通ユーティリティを提供するモジュール.

軽量な基底クラスとしてロガー提供などの共通機能をまとめます.
"""

from __future__ import annotations

from app.utils.logger import get_logger


class BaseViewService:
    """Views 配下のサービス共通の基底クラス.

    現時点ではロガー提供のみを行う軽量な基底クラス。
    将来的に共通のユーティリティやライフサイクル管理を追加できます.
    """

    def __init__(self) -> None:
        """ロガーを初期化してインスタンスに割り当てます."""
        self.logger = get_logger(self.__class__.__module__)
