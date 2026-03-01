"""業種21: 陸運業のスクリーニング戦略。"""

from __future__ import annotations

from app.services.screening.base_strategy import BaseScreeningStrategy
from app.services.screening.models import ScreeningConfig, ScreeningScoreConfig, ScreeningThresholds


class Industry21LandTransportationStrategy(BaseScreeningStrategy):
    """業種21: 陸運業 (Land Transportation)のスクリーニング戦略。

    現在はデフォルト設定を使用しています。
    将来的に業種固有のルール（閾値やスコア重み）が必要になった場合、
    このクラスをオーバーライドして実装してください。
    """

    @staticmethod
    def get_default_config() -> ScreeningConfig:
        """デフォルト設定を取得。

        業種: 陸運業 (Land Transportation)

        カスタマイズする場合は、thresholds や score_config を変更してください。
        """
        return ScreeningConfig(
            industry_code="21",
            industry_name="陸運業",
            thresholds=ScreeningThresholds(),
            score_config=ScreeningScoreConfig(),
        )
