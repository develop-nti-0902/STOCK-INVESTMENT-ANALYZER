"""業種05: 繊維製品のスクリーニング戦略。"""

from __future__ import annotations

from app.services.screening.base_strategy import BaseScreeningStrategy
from app.services.screening.models import ScreeningConfig, ScreeningScoreConfig, ScreeningThresholds


class Industry05TextilesStrategy(BaseScreeningStrategy):
    """業種05: 繊維製品 (Textiles)のスクリーニング戦略。

    現在はデフォルト設定を使用しています。
    将来的に業種固有のルール（閾値やスコア重み）が必要になった場合、
    このクラスをオーバーライドして実装してください。
    """

    @staticmethod
    def get_default_config() -> ScreeningConfig:
        """デフォルト設定を取得。

        業種: 繊維製品 (Textiles)

        カスタマイズする場合は、thresholds や score_config を変更してください。
        """
        return ScreeningConfig(
            industry_code="05",
            industry_name="繊維製品",
            thresholds=ScreeningThresholds(),
            score_config=ScreeningScoreConfig(),
        )
