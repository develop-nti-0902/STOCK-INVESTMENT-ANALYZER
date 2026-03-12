"""業種29: 証券・商品先物取引業のスクリーニング戦略。"""

from __future__ import annotations

from app.services.screening.base_strategy import BaseScreeningStrategy
from app.services.screening.models import ScreeningConfig, ScreeningScoreConfig, ScreeningThresholds


class Industry29SecuritiesStrategy(BaseScreeningStrategy):
    """業種29: 証券・商品先物取引業 (Securities and Commodity Futures)のスクリーニング戦略。

    現在はデフォルト設定を使用しています。
    将来的に業種固有のルール（閾値やスコア重み）が必要になった場合、
    このクラスをオーバーライドして実装してください。
    """

    @staticmethod
    def get_default_config() -> ScreeningConfig:
        """デフォルト設定を取得。

        業種: 証券・商品先物取引業 (Securities and Commodity Futures)

        カスタマイズする場合は、thresholds や score_config を変更してください。
        """
        return ScreeningConfig(
            industry_code="29",
            industry_name="証券・商品先物取引業",
            thresholds=ScreeningThresholds(),
            score_config=ScreeningScoreConfig(),
        )
