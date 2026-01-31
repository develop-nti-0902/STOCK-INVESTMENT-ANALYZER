from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseParser(ABC):
    """共通パーサーの抽象基底クラス。

    サブクラスは `parse` と `validate_data` を実装する必要があります。
    """

    @abstractmethod
    def parse(self, data: Any) -> Dict[str, Any]:
        """与えられたデータを解析して辞書を返す。

        Args:
            data: パーサーに渡される生データ（ファイルパス、バイナリ、文字列等）

        Returns:
            パース結果を表す辞書
        """

    @abstractmethod
    def validate_data(self, data: Any) -> bool:
        """渡されたデータがパーサーの期待する形式か検証する。

        Returns:
            検証に成功すれば True
        """
