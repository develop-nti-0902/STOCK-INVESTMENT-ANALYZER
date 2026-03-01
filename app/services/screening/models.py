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


# 17業種区分に対応するデフォルト設定辞書
# JPX業種分類に基づく
INDUSTRY_CONFIGS: Dict[str, ScreeningConfig] = {
    "01": ScreeningConfig(industry_code="01", industry_name="水産・農林業"),
    "02": ScreeningConfig(industry_code="02", industry_name="鉱業"),
    "03": ScreeningConfig(industry_code="03", industry_name="建設業"),
    "04": ScreeningConfig(industry_code="04", industry_name="食料品"),
    "05": ScreeningConfig(industry_code="05", industry_name="繊維製品"),
    "06": ScreeningConfig(industry_code="06", industry_name="パルプ・紙"),
    "07": ScreeningConfig(industry_code="07", industry_name="化学"),
    "08": ScreeningConfig(industry_code="08", industry_name="医薬品"),
    "09": ScreeningConfig(industry_code="09", industry_name="石油・石炭製品"),
    "10": ScreeningConfig(industry_code="10", industry_name="ゴム製品"),
    "11": ScreeningConfig(industry_code="11", industry_name="ガラス・土石製品"),
    "12": ScreeningConfig(industry_code="12", industry_name="鉄鋼"),
    "13": ScreeningConfig(industry_code="13", industry_name="非鉄金属"),
    "14": ScreeningConfig(industry_code="14", industry_name="金属製品"),
    "15": ScreeningConfig(industry_code="15", industry_name="機械"),
    "16": ScreeningConfig(industry_code="16", industry_name="電気機器"),
    "17": ScreeningConfig(industry_code="17", industry_name="輸送用機器"),
    "18": ScreeningConfig(industry_code="18", industry_name="精密機器"),
    "19": ScreeningConfig(industry_code="19", industry_name="その他製品"),
    "20": ScreeningConfig(industry_code="20", industry_name="電気・ガス業"),
    "21": ScreeningConfig(industry_code="21", industry_name="陸運業"),
    "22": ScreeningConfig(industry_code="22", industry_name="海運業"),
    "23": ScreeningConfig(industry_code="23", industry_name="空運業"),
    "24": ScreeningConfig(industry_code="24", industry_name="倉庫・運輸関連業"),
    "25": ScreeningConfig(industry_code="25", industry_name="情報・通信業"),
    "26": ScreeningConfig(industry_code="26", industry_name="卸売業"),
    "27": ScreeningConfig(industry_code="27", industry_name="小売業"),
    "28": ScreeningConfig(industry_code="28", industry_name="銀行業"),
    "29": ScreeningConfig(industry_code="29", industry_name="証券・商品先物取引業"),
    "30": ScreeningConfig(industry_code="30", industry_name="保険業"),
    "31": ScreeningConfig(industry_code="31", industry_name="その他金融業"),
    "32": ScreeningConfig(industry_code="32", industry_name="不動産業"),
    "33": ScreeningConfig(industry_code="33", industry_name="サービス業"),
}
