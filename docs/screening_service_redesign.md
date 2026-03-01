# スクリーニングサービス再設計完了

## 📋 実装サマリ

Strategyパターンを用いた、業種別カスタマイズ可能なスクリーニングサービス構造が完成しました。

## 🏗️ 新アーキテクチャ

```
app/services/screening/
  ├── models.py                    # 共通モデル＋33業種設定
  ├── base_strategy.py             # 抽象基底戦略クラス
  ├── strategy_factory.py          # ファクトリ（業種→戦略のマッピング）
  ├── screening_service.py         # 新サービス（Strategyパターン対応）✨
  ├── simple_screening_service.py  # レガシーサービス（互換性維持）
  ├── strategies/                  # 業種別戦略（拡張ポイント）
  │   ├── __init__.py
  │   └── industry_01_water.py     # テンプレート例
  └── __init__.py                  # 公開インターフェース
```

## 🎯 主要コンポーネント

### 1. models.py
- `ScreeningResult`: 評価結果
- `ScreeningThresholds`: 必須条件の閾値（業種別カスタマイズ可能）
- `ScreeningScoreConfig`: スコア計算の設定（業種別カスタマイズ可能）
- `ScreeningConfig`: 業種別全体設定
- `INDUSTRY_CONFIGS`: 33業種のデフォルト設定辞書

### 2. base_strategy.py
`BaseScreeningStrategy` 抽象クラス
- 共通のスクリーニングロジック実装
- メソッド：
  - `evaluate_with_history()`: 履歴データを使用した評価
  - `_check_dividend_continuity()`: 配当継続性チェック
  - `_check_eps_health()`: EPS健全性チェック
  - `_check_operating_cf()`: 営業CFチェック
  - `_score_dividend()`: 配当スコア計算
  - `_score_eps()`: EPS スコア計算
  - `_score_stability()`: 安定性スコア計算
  - `_score_profitability()`: 収益性スコア計算

### 3. strategy_factory.py
`ScreeningStrategyFactory` ファクトリクラス
- `create(industry_code)`: 業種コードからストラテジーを生成
- `get_config(industry_code)`: 業種設定を取得
- `customize_config()`: 既存設定をカスタマイズ

キャッシング機能により、頻繁に使用される戦略は効率的に管理されます。

### 4. screening_service.py（新）
`ScreeningService`: 新しいメインサービス
- `run()`: スクリーニング実行（レガシーと互換）
- `evaluate()`: 単一銘柄評価（業種別ストラテジー使用）
- 自動的に業種コードを検出し、対応するストラテジーを適用

### 5. simple_screening_service.py（レガシー）
- 既存実装は維持
- 段階的移行が可能

## 🔄 処理フロー

```
ユーザー呼び出し
    ↓
ScreeningService.run()
    ↓
各銘柄について：
    ├─ 業種コード（sector_code_17）を取得
    ├─ ScreeningStrategyFactory で業種別戦略を生成
    └─ BaseScreeningStrategy.evaluate_with_history() で評価
         ├─ 必須条件チェック（配当、EPS、CF）
         ├─ スコア計算（4つの観点）
         └─ ステータス判定（優先、活動中、監視、不適格）
    ↓
結果を DB に保存＆出力
```

## 📊 33業種対応表

| コード | 業種名               |
| ------ | -------------------- |
| 01     | 水産・農林業         |
| 02     | 鉱業                 |
| 03     | 建設業               |
| 04     | 食料品               |
| 05     | 繊維製品             |
| 06     | パルプ・紙           |
| 07     | 化学                 |
| 08     | 医薬品               |
| 09     | 石油・石炭製品       |
| 10     | ゴム製品             |
| 11     | ガラス・土石製品     |
| 12     | 鉄鋼                 |
| 13     | 非鉄金属             |
| 14     | 金属製品             |
| 15     | 機械                 |
| 16     | 電気機器             |
| 17     | 輸送用機器           |
| 18     | 精密機器             |
| 19     | その他製品           |
| 20     | 電気・ガス業         |
| 21     | 陸運業               |
| 22     | 海運業               |
| 23     | 空運業               |
| 24     | 倉庫・運輸関連業     |
| 25     | 情報・通信業         |
| 26     | 卸売業               |
| 27     | 小売業               |
| 28     | 銀行業               |
| 29     | 証券・商品先物取引業 |
| 30     | 保険業               |
| 31     | その他金融業         |
| 32     | 不動産業             |
| 33     | サービス業           |

## 🚀 今後の拡張方法

### 業種固有のルールを追加する場合

**例：化学業界（業種07）の特別ルール**

```python
# app/services/screening/strategies/industry_07_chemistry.py
from app.services.screening.base_strategy import BaseScreeningStrategy
from app.services.screening.models import ScreeningConfig, ScreeningThresholds, ScreeningScoreConfig

class IndustryChemistryStrategy(BaseScreeningStrategy):
    """化学業界向けカスタムスクリーニング戦略。

    例：化学業界では高い営業利益率を重視し、
    配当よりもキャッシュフロー安定性を優先する。
    """

    @staticmethod
    def get_default_config() -> ScreeningConfig:
        # カスタム設定
        custom_thresholds = ScreeningThresholds(
            dividend_min_years=3,  # 配当は3年で許可
            cf_min_positive_years=5,  # CF は厳しく
        )

        custom_score_config = ScreeningScoreConfig(
            dividend_max_score=20,  # 配当スコア削減
            stability_max_score=30,  # 安定性重視
        )

        return ScreeningConfig(
            industry_code="07",
            industry_name="化学",
            thresholds=custom_thresholds,
            score_config=custom_score_config,
        )
```

その後、`ScreeningStrategyFactory._load_custom_strategy()` を実装して、
業種別ファイルから動的にロードするようにすれば完成です。

### 現在の実装では
すべての業種が `DefaultScreeningStrategy`（共通ルール）を使用しており、
必要になった時点で個別戦略ファイルを追加可能な設計になっています。

## ✅ 利点

| 項目         | 説明                                       |
| ------------ | ------------------------------------------ |
| **拡張性**   | 新業種追加や既存業種のカスタマイズが容易   |
| **保守性**   | ロジックが適切に分離され、変更影響が局所化 |
| **テスト性** | 各戦略を独立してテスト可能                 |
| **互換性**   | レガシーサービスを並行稼働可能             |
| **設定管理** | 閾値・スコア設定を一元管理                 |

## 📝 使用例

```python
from app.services.screening import ScreeningService, ScreeningStrategyFactory

# 新サービスを利用
service = ScreeningService(
    financial_query_service=fq,
    stock_master_maker=stock_master_session_maker,
    screening_result_maker=result_session_maker,
)

# 全銘柄をスクリーニング
await service.run(sec_codes=None, evaluation_date=date.today())

# または、戦略ファクトリで直接カスタマイズ可能
factory = ScreeningStrategyFactory()
custom_config = factory.customize_config(
    industry_code="12",  # 鉄鋼
    thresholds=ScreeningThresholds(dividend_min_years=2),
)
strategy = factory.create("12")
```

## 🔗 関連ファイル

- DB スキーマ: [stock_master](app/models/market_data/stock_master/stock_master.py)
- 業種情報: `sector_code_17` / `sector_name_17` カラム

## 📌 次のステップ

1. ✅ 基本実装完了
2. ⬜ デプロイとテスト
3. ⬜ 個別業種ルールの追加（必要に応じて）
4. ⬜ レガシーサービスからの段階的移行

---

**実装日**: 2026年2月28日
**ステータス**: ✅ 完成
