"""スクリーニングサービスの共通モデルと設定クラスを定義するモジュール。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


# pylint: disable=R0902
@dataclass
class ScreeningResult:
    """単一銘柄のスクリーニング結果を表す dataclass。"""

    sec_code: str
    pass_required: bool
    total_score: int
    score_dividend: int
    score_eps: int
    score_stability: int
    score_profitability: int
    status: str
    failed_conditions: List[str]
    fiscal_year_end: Optional[date]


@dataclass
class ScreeningThresholds:
    """必須条件チェックの閾値を定義するクラス。"""

    # 配当関連
    dividend_min_years: int = 5  # 過去N年間の配当継続性を確認
    dividend_max_decline_years: int = 0  # 減配を許容する年の上限（0=許さない）
    dividend_min_consecutive_increase: int = 3  # 最小連続増配年数

    # EPS関連
    eps_min_positive_years: int = 5  # EPS が正であるべき最小年数
    eps_max_consecutive_decline: int = 1  # 連続減少を許容する年数
    eps_decline_max_rate: float = 0.30  # EPS 減少時の最大許容率（30%）

    # キャッシュフロー関連
    cf_min_positive_years: int = 4  # 営業CF がプラスであるべき最小年数


# pylint: disable=R0902
@dataclass
class ScreeningScoreConfig:
    """スクリーニングのスコア計算設定を定義するクラス。"""

    # 配当スコア
    dividend_max_score: int = 30
    dividend_all_increase_score: int = 10  # 5年間連続増配
    dividend_growth_rate_threshold: float = 0.05  # 5%以上の平均増配率
    dividend_growth_rate_score: int = 10
    dividend_tau_threshold: float = 0.4  # Kendall τ > 0.4
    dividend_tau_score: int = 10

    # EPS スコア
    eps_max_score: int = 30
    eps_growth_years_threshold: int = 3  # 増加年が3年以上
    eps_growth_years_score: int = 10
    eps_consecutive_growth_threshold: int = 3  # 3年連続増加
    eps_consecutive_growth_score: int = 10
    eps_tau_threshold: float = 0.4
    eps_tau_score: int = 10

    # 安定性スコア
    stability_max_score: int = 20
    stability_sales_growth_threshold: int = 3  # 売上増加年が3年以上
    stability_sales_growth_score: int = 10
    stability_margin_growth_threshold: int = 3  # 営業利益増加年が3年以上
    stability_margin_growth_score: int = 10

    # 収益性スコア
    profitability_max_score: int = 20
    profitability_decline_years_threshold: int = 2  # マージン低下年が2年以下
    profitability_decline_score: int = 10
    profitability_consecutive_decline_threshold: float = 2.0  # 2.0pt以上
    profitability_consecutive_decline_score: int = 10

    # ステータス判定の総スコア閾値
    status_priority_threshold: int = 90
    status_active_threshold: int = 80
    status_watch_threshold: int = 70


@dataclass
class ScreeningConfig:
    """業種別スクリーニング設定を定義するクラス。"""

    industry_code: str  # 業種コード (01-17)
    industry_name: str  # 業種名
    thresholds: ScreeningThresholds = field(default_factory=ScreeningThresholds)
    score_config: ScreeningScoreConfig = field(default_factory=ScreeningScoreConfig)

    # 業種固有のカスタマイズ用フィールド（将来用）
    custom_params: Dict[str, Any] = field(default_factory=dict)
