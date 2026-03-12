"""スクリーニング戦略のファクトリクラス。

業種コードから対応するスクリーニング戦略インスタンスを生成します。
"""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

from app.services.screening.base_strategy import BaseScreeningStrategy
from app.services.screening.models import ScreeningResult

if TYPE_CHECKING:
    from app.services.screening.screening_service import ScreeningService

logger = logging.getLogger(__name__)


class DefaultScreeningStrategy(BaseScreeningStrategy):
    """デフォルトのスクリーニング戦略。

    全ての業種で共通のロジックを使用します。
    業種固有のルールが必要になった時点で、
    サブクラスを作成してオーバーライドできます。
    """

    async def evaluate(
        self, sec_code: str, _evaluation_date: date, **kwargs: Any
    ) -> ScreeningResult:
        """抽象メソッドの実装。実際には evaluate_with_history を使用します。"""
        raise NotImplementedError("Call evaluate_with_history with history data instead")


class ScreeningStrategyFactory:
    """スクリーニング戦略を業種別に生成するファクトリクラス。

    業種コードから対応するストラテジーインスタンスを作成します。
    将来、業種固有のルール（閾値やスコア計算）が必要になった場合は、
    _load_custom_strategy メソッドで専用クラスをロードできます。
    """

    # 業種別カスタム戦略クラスを保持するキャッシュ
    _strategy_cache: Dict[str, type[BaseScreeningStrategy]] = {}

    @classmethod
    def create(
        cls,
        industry_code: str,
        screening_service: Optional["ScreeningService"] = None,
    ) -> BaseScreeningStrategy:
        """業種コードに対応するスクリーニング戦略インスタンスを生成。

        screening_service が必須です。DB から業種設定を取得します。

        Args:
            industry_code: 業種コード（"01" ~ "33"）
            screening_service: ScreeningService インスタンス（DB キャッシュ取得用）

        Returns:
            BaseScreeningStrategy: インスタンス化されたスクリーニング戦略

        Raises:
            ValueError: screening_service が None の場合、または業種コードが見つからない場合
        """
        # screening_service が必須
        if screening_service is None:
            raise ValueError("screening_service is required to create strategy")

        # DB キャッシュから業種設定を取得
        config = screening_service.get_industry_config(industry_code)
        if config is None:
            raise ValueError(f"Industry code {industry_code} not found in database")

        # カスタム戦略クラスの読み込み（既存ロジック）
        strategy_class = cls._load_custom_strategy(industry_code)

        # 戦略インスタンスの生成
        return strategy_class(config)

    @classmethod
    def _load_custom_strategy(cls, industry_code: str) -> type[BaseScreeningStrategy]:
        """業種固有のカスタム戦略クラスをロード。

        キャッシュをチェックし、見つからない場合はデフォルト戦略を返します。
        将来、業種固有カスタム戦略が必要になった場合は、
        このメソッドで動的インポートを実装します。

        Args:
            industry_code: 業種コード

        Returns:
            BaseScreeningStrategy のサブクラス
        """
        # キャッシュから取得
        if industry_code in cls._strategy_cache:
            return cls._strategy_cache[industry_code]

        # 将来の拡張: カスタム戦略ファイルからの動的インポート
        # 例: app.services.screening.strategies.industry_XX_YYY
        # 本実装では、全業種で DefaultScreeningStrategy を使用
        strategy_class = DefaultScreeningStrategy

        # キャッシュに保存
        cls._strategy_cache[industry_code] = strategy_class

        return cast(type[BaseScreeningStrategy], strategy_class)
