"""スクリーニング戦略のファクトリクラス。

業種コードから対応するスクリーニング戦略インスタンスを生成します。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, Optional, cast

from app.services.screening.base_strategy import BaseScreeningStrategy
from app.services.screening.models import (
    INDUSTRY_CONFIGS,
    ScreeningConfig,
    ScreeningResult,
    ScreeningScoreConfig,
    ScreeningThresholds,
)

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
    def create(cls, industry_code: str) -> BaseScreeningStrategy:
        """業種コードに対応するスクリーニング戦略インスタンスを生成。

        Args:
            industry_code: 業種コード（"01" ~ "33"）

        Returns:
            BaseScreeningStrategy: インスタンス化されたスクリーニング戦略

        Raises:
            ValueError: 業種コードが無効な場合
        """
        if industry_code not in INDUSTRY_CONFIGS:
            raise ValueError(
                f"Invalid industry_code: {industry_code}. "
                f"Valid codes: {', '.join(sorted(INDUSTRY_CONFIGS.keys()))}"
            )

        # 業種設定を取得
        config = INDUSTRY_CONFIGS[industry_code]

        # キャッシュからカスタム戦略クラスをロード（存在すれば）
        strategy_class = cls._load_custom_strategy(industry_code)

        # インスタンスを生成して返す
        return strategy_class(config)

    @classmethod
    def _load_custom_strategy(cls, industry_code: str) -> type[BaseScreeningStrategy]:
        """業種固有のカスタム戦略クラスをロード。

        キャッシュをチェックし、見つからない場合は動的インポートを試みます。
        カスタム戦略が存在しない場合はデフォルト戦略を返します。

        Args:
            industry_code: 業種コード

        Returns:
            BaseScreeningStrategy のサブクラス
        """
        # キャッシュから取得
        if industry_code in cls._strategy_cache:
            return cls._strategy_cache[industry_code]

        # 業種設定から業種名を取得
        config = INDUSTRY_CONFIGS.get(industry_code)
        if config is None:
            return cast(type[BaseScreeningStrategy], DefaultScreeningStrategy)

        # 将来の拡張: カスタム戦略ファイルからの動的インポート
        # 例: app.services.screening.strategies.industry_XX_YYY
        # 本実装では、全業種で DefaultScreeningStrategy を使用
        strategy_class = DefaultScreeningStrategy

        # キャッシュに保存
        cls._strategy_cache[industry_code] = strategy_class

        return cast(type[BaseScreeningStrategy], strategy_class)

    @classmethod
    def get_config(cls, industry_code: str) -> ScreeningConfig:
        """業種に対応するスクリーニング設定を取得。

        Args:
            industry_code: 業種コード

        Returns:
            ScreeningConfig: 業種別設定

        Raises:
            ValueError: 業種コードが無効な場合
        """
        if industry_code not in INDUSTRY_CONFIGS:
            raise ValueError(
                f"Invalid industry_code: {industry_code}. "
                f"Valid codes: {', '.join(sorted(INDUSTRY_CONFIGS.keys()))}"
            )

        return INDUSTRY_CONFIGS[industry_code]

    @classmethod
    def customize_config(
        cls,
        industry_code: str,
        thresholds: Optional[ScreeningThresholds] = None,
        score_config: Optional[ScreeningScoreConfig] = None,
    ) -> ScreeningConfig:
        """既存の業種設定をカスタマイズして返す。

        Args:
            industry_code: 業種コード
            thresholds: カスタム閾値設定（None の場合はデフォルト）
            score_config: カスタムスコア設定（None の場合はデフォルト）

        Returns:
            ScreeningConfig: カスタマイズされた設定

        Raises:
            ValueError: 業種コードが無効な場合
        """
        base_config = cls.get_config(industry_code)

        # 既存設定をコピー して、カスタマイズ部分のみ上書き
        custom_config = ScreeningConfig(
            industry_code=base_config.industry_code,
            industry_name=base_config.industry_name,
            thresholds=thresholds or base_config.thresholds,
            score_config=score_config or base_config.score_config,
            custom_params=base_config.custom_params.copy(),
        )

        return custom_config
