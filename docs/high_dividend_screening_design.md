# 高配当株スクリーニングシステム 設計書

## 1. システム概要

### 1.1 目的

高配当株投資ルールに基づいて、銘柄のスクリーニング、監視、購入判断、売却判断を自動化するシステムを構築する。

### 1.2 4つのフェーズ

```mermaid
graph LR
    A[全銘柄] --> B[スクリーニング<br/>必須条件判定]
    B --> C[スクリーニング<br/>ポイント評価]
    C --> D[監視リスト<br/>70点以上]
    D --> E[購入候補<br/>配当利回り判定]
 5. 処理（同期実行）作成
```

1. **スクリーニング**: 財務指標で企業の質を判定（年1回更新）
2. **監視**: 株価・配当利回りで買い時を判定（日次更新）
---
## 2. データモデル設計

## ファイル構成

この設計に基づいて新たに作成する（もしくは配置を想定する）主要ファイル・ディレクトリ構成を示します。実装時は既存のプロジェクト構成に合わせてファイルを追加してください。

### 実装スコープ（本ドキュメントで優先する範囲）

- 本フェーズの優先実装範囲: バックエンドの処理（ルール評価 → スコア計算 → `screening_results`/`watch_list` への永続化）までを対象とします。
- フロントエンド（画面/UI）は後工程とし、本ドキュメントでは詳細設計・ファイル作成は行いません。
- 優先で作成するファイル群: `app/models/screening/*`, `app/repositories/screening/*`, `app/services/screening/*`, `scripts/batch/*`, `alembic/versions/*`。
- フロントエンド関連ファイルや画面仕様はPhase 4（実装完了後）で別途追加します。

 - app/
        - models/
            - screening/
                - screening_result.py       # `ScreeningResult` ORMモデル
                - watch_list.py             # `WatchList` ORMモデル
        - repositories/
            - screening/
                - screening_result_repository.py  # `ScreeningResultRepository` (CRUD, upsert)
                - watch_list_repository.py        # `WatchListRepository`
            - rule_repository.py              # ルール定義の読み書き（ファイル or DB）
        - services/
            - screening/
                - rule_engine.py           # ルール読み込み・条件評価・スコア合成
                - screening_service.py     # スクリーニング実行・結果永続化
                - watch_list_service.py    # 監視リスト更新・購入候補抽出
                - financial_analysis_service.py  # 配当/EPS/CF取得・トレンド計算
        - api/
            - v1/
                - screening.py             # POST /api/v1/screening/execute 等
                - watch_list.py            # 監視リスト関連API

- scripts/
    - batch/
        - batch_screening.py                 # 年次スクリーニング実行バッチ
        - batch_update_watch_list_prices.py  # 日次価格更新バッチ

- app/rules/
    - core_v1.yaml                # 運用ルールセット（YAML）

- alembic/versions/
    - <timestamp>_create_screening_and_watchlist_tables.py  # マイグレーション

注意:
- 既存の `edinet_*` モデルやリポジトリは流用します。新規モデルは既存DB設計（`alembic`）と整合させてください。
- ルールと演算子（operator）は `rule_engine.py` 側でプラグイン的に追加できる設計を推奨します。

---

## 2. データモデル設計

### 2.1 既存テーブル（財務データ）

以下のテーブルは既に実装済み：

- `edinet_profit_and_loss`: 損益計算書（売上高、営業利益、EPS）
- `edinet_cash_flow_statement`: キャッシュフロー計算書（営業CF）
- `edinet_stock_dividend`: 配当データ（年間配当金実績）

### 2.2 新規テーブル（スクリーニング結果）

#### screening_results（スクリーニング結果）

銘柄ごとのスクリーニング結果を保存する。

| カラム名                 | 型          | NULL | 説明                                 |
| ------------------------ | ----------- | ---- | ------------------------------------ |
| id                       | INTEGER     | NO   | 主キー                               |
| sec_code                 | VARCHAR(10) | NO   | 証券コード                           |
| evaluation_date          | DATE        | NO   | 評価実施日                           |
| fiscal_year_end          | DATE        | NO   | 評価対象の最新決算期末日             |
| pass_required_conditions | BOOLEAN     | NO   | 必須条件クリアフラグ                 |
| total_score              | INTEGER     | NULL | 総合スコア（0-100点）                |
| score_dividend           | INTEGER     | NULL | 配当実績スコア（0-30点）             |
| score_eps                | INTEGER     | NULL | EPS成長スコア（0-30点）              |
| score_stability          | INTEGER     | NULL | 事業安定性スコア（0-20点）           |
| score_profitability      | INTEGER     | NULL | 収益性維持スコア（0-20点）           |
| status                   | VARCHAR(20) | NO   | ステータス（候補外/監視/積極/優先）  |
| failed_conditions        | JSONB       | NULL | 不合格となった条件リスト             |
| screening_details        | JSONB       | NULL | スクリーニング詳細データ（JSON形式） |
| created_at               | TIMESTAMP   | NO   | レコード作成日時                     |
| updated_at               | TIMESTAMP   | NO   | レコード更新日時                     |

**ユニーク制約**: `(sec_code, evaluation_date)`

#### watch_list（監視リスト）

監視対象銘柄（70点以上）の最新状態を管理する。

| カラム名            | 型             | NULL | 説明                             |
| ------------------- | -------------- | ---- | -------------------------------- |
| id                  | INTEGER        | NO   | 主キー                           |
| sec_code            | VARCHAR(10)    | NO   | 証券コード                       |
| screening_result_id | INTEGER        | NO   | スクリーニング結果ID（FK）       |
| current_price       | NUMERIC(10, 2) | NULL | 最新株価                         |
| dividend_yield      | NUMERIC(5, 2)  | NULL | 配当利回り（%）                  |
| watch_level         | VARCHAR(20)    | NO   | 監視レベル（監視強化/検討/優先） |
| status              | VARCHAR(20)    | NO   | ステータス（監視中/購入済/除外） |
| added_date          | DATE           | NO   | 監視リスト追加日                 |
| last_updated        | TIMESTAMP      | NO   | 最終更新日時                     |
| notes               | TEXT           | NULL | メモ                             |

**ユニーク制約**: `sec_code`（1銘柄1レコード）


---

## 3. サービス層設計

### 3.1 ScreeningService（スクリーニングサービス）
**責務**: スクリーニングルールを外部定義（YAML/JSON）で管理し、ルールエンジンで柔軟に評価・スコアリングする。

設計方針:
- ルールはコードにハードコーディングせず、`app/rules/` または `config/rules.yaml` で定義する。運用中にルールセットを切り替えられるようにする。
- ルールは小さい単位（条件）を組み合わせて1つの評価ルール（スコア配分）を構成する。各条件は比較演算子・閾値・重みを持ち、評価時に合算して総合スコアを算出する。
- ルールはバージョン管理・有効/無効フラグ・優先度を持つ。

主要コンポーネント:
- `RuleEngine` (`app/services/screening/rule_engine.py`): ルールの読み込み、検証、個別条件の評価、スコア合成を行う。
- `RuleRepository` (`app/repositories/screening/rule_repository.py`): ルール定義のCRUD（DB またはファイルストア）。
- `ScreeningService` (`app/services/screening/screening_service.py`): ルールエンジンを呼び出し、`ScreeningResult` を生成する責務。実行は同期処理（CLI / API 呼び出し）を想定する。

主要メソッド例:

```python
class ScreeningService:
        def __init__(self, rule_engine: RuleEngine, rule_repo: RuleRepository):
                self.rule_engine = rule_engine
                self.rule_repo = rule_repo

        def execute_screening(self, sec_codes: list[str], evaluation_date: date, rule_set_id: str | None = None) -> list[ScreeningResult]:
                """全銘柄のスクリーニングを同期的に実行。rule_set_id で使用するルールセットを切替可能。"""

        def evaluate_for_security(self, sec_code: str, rule_set: RuleSet) -> ScreeningResult:
                """単一銘柄に対してルールセットを評価し、詳細スコアを返す。"""

        def load_rule_set(self, rule_set_id: str) -> RuleSet:
                """RuleRepository からルールセットを取得して `RuleEngine` 用に整形する。"""
```

ルール定義の例（YAML）:

```yaml
id: core_v1
version: 2026-02-14
description: 基本スクリーニングルールセット
enabled: true
rules:
    - id: dividend_continuity
        weight: 30
        conditions:
            - metric: dividends
                operator: reduce_trend_increase_years
                params: {years: 5, min_years: 3}
            - metric: dividends
                operator: consecutive_increase
                params: {years: 2}
    - id: eps_growth
        weight: 30
        conditions:
            - metric: eps
                operator: positive_all_years
                params: {years: 5}
            - metric: eps
                operator: kendall_tau
                params: {threshold: 0.4}
```

この形式により、新しい条件（operator）を `RuleEngine` に追加するだけで運用ルールを拡張可能です。

評価時の流れ:
1. `ScreeningService` が `RuleRepository` から有効な `RuleSet` を取得
2. `RuleEngine` が各銘柄の指標（配当/EPS/CF/営業利益率 等）を `FinancialAnalysisService` から取得
3. 個々の条件を評価し、条件ごとの点数・重みづけで合算して総合スコアを算出
4. `ScreeningResult` を作成・永続化し、`WatchListService` で監視リストを更新

利点:
- ルールの変更・追加がコード変更不要で行える（運用設定で対応）
- ルールのABテスト、バージョン比較が容易
- 条件の複雑化（複合条件、閾値テーブル、セクター別補正等）へ柔軟に対応可能


### 3.2 WatchListService（監視リストサービス）

**責務**: 監視リストの管理と株価監視

**主要メソッド**:

```python
class WatchListService:
    async def update_watch_list(
        self,
        screening_results: list[ScreeningResult]
    ) -> None:
        """スクリーニング結果から監視リストを更新（70点以上）"""
        pass

    async def update_stock_prices(self) -> None:
        """監視銘柄の最新株価と配当利回りを更新"""
        pass

    async def get_purchase_candidates(
        self,
        min_yield: float = 3.5
    ) -> list[WatchListItem]:
        """購入候補銘柄を取得（配当利回り条件付き）"""
        pass
```


### 3.5 FinancialAnalysisService（財務分析サービス）

**責務**: 財務データの取得と計算

**主要メソッド**:

```python
class FinancialAnalysisService:
    async def get_dividend_history(
        self,
        sec_code: str,
        years: int = 5
    ) -> list[DividendRecord]:
        """過去N年の配当履歴を取得"""
        pass

    async def calculate_dividend_trend(
        self,
        dividends: list[float]
    ) -> float:
        """配当トレンドを計算（Kendallのτ）"""
        pass

    async def get_eps_history(
        self,
        sec_code: str,
        years: int = 5
    ) -> list[EPSRecord]:
        """過去N年のEPS履歴を取得"""
        pass

    async def calculate_eps_trend(
        self,
        eps_list: list[float]
    ) -> float:
        """EPSトレンドを計算（Kendallのτ）"""
        pass

    async def get_operating_cf_history(
        self,
        sec_code: str,
        years: int = 5
    ) -> list[CFRecord]:
        """過去N年の営業CF履歴を取得"""
        pass

    async def calculate_operating_margin_trend(
        self,
        sec_code: str,
        years: int = 5
    ) -> OperatingMarginTrend:
        """営業利益率のトレンドを計算"""
        pass
```

---

## 4. リポジトリ層設計

### 4.1 既存リポジトリの活用

- `EdinetProfitAndLossRepository`: PL取得
- `EdinetCashFlowStatementRepository`: CF取得
- `EdinetStockDividendRepository`: 配当取得

### 4.2 新規リポジトリ

- `ScreeningResultRepository`: スクリーニング結果のCRUD
- `WatchListRepository`: 監視リストのCRUD


---

## 5. API設計

### 5.1 スクリーニングAPI

#### POST /api/v1/screening/execute
スクリーニングを実行する。

**リクエスト**:
```json
{
  "sec_codes": ["7203", "6758"],  // オプション、未指定時は全銘柄
  "evaluation_date": "2026-02-14"  // オプション、未指定時は本日
}
```

**レスポンス**:
```json
{
  "evaluation_date": "2026-02-14",
  "total_evaluated": 100,
  "passed_required": 45,
  "watch_list_count": 30,
  "results": [
    {
      "sec_code": "7203",
      "company_name": "トヨタ自動車",
      "passed_required": true,
      "total_score": 85,
      "status": "積極的に検討"
    }
  ]
}
```

#### GET /api/v1/screening/results
スクリーニング結果を取得する。

**クエリパラメータ**:
- `evaluation_date`: 評価日（デフォルト: 最新）
- `min_score`: 最小スコア（デフォルト: 70）
- `status`: ステータスフィルター


#### POST /api/v1/watch-list/update-prices
監視銘柄の株価を更新する。

---

## 6. 処理設計（同期処理）

### 6.1 年次処理（決算更新時、同期実行）

#### batch_screening.py
- **実行タイミング**: 年1回、各企業の決算発表後
- **処理内容**:
  1. EDINET APIから最新財務データを取得
  2. 全銘柄のスクリーニングを実行
    3. 監視リストを更新
    4. 結果をメール通知

### 6.2 日次処理（営業日毎、同期実行）

#### batch_update_watch_list_prices.py
- **実行タイミング**: 平日毎日、取引終了後
- **処理内容**:
  1. 監視銘柄の最新株価を取得（Yahoo Finance API）
  2. 配当利回りを再計算
  3. 購入候補銘柄を抽出
  4. 配当利回り条件を満たす銘柄を通知

---

## 7. 計算ロジック概要

### 7.1 必須条件チェック

#### 配当の継続性
```python
def check_dividend_continuity(dividends: list[float]) -> bool:
    """
    過去5年間の配当データをチェック
    - 減配回数が2回以下
    - 直近2年間で連続減配がない
    """
    pass
```

#### EPSの健全性
```python
def check_eps_health(eps_list: list[float]) -> bool:
    """
    過去5年間のEPSをチェック
    - 赤字（EPS ≤ 0）がない
    - 直近2年間で連続減少がない
    - 直近1年間の減少率が30%未満
    """
    pass
```

#### 営業キャッシュフロー
```python
def check_operating_cf(cf_list: list[float]) -> bool:
    """
    過去5年間の営業CFをチェック
    - 4年以上プラス
    """
    pass
```

### 7.2 スコア計算

#### A. 配当実績（30点）
```python
def calculate_dividend_score(dividends: list[float]) -> int:
    """
    - 増配年が3年以上: +10
    - 2年以上連続増配: +10
    - トレンド上向き（τ > 0.4）: +10
    """
    pass
```

#### B. EPS成長（30点）
```python
def calculate_eps_score(eps_list: list[float]) -> int:
    """
    - EPS増加年が3年以上: +10
    - 2年以上連続増加: +10
    - トレンド上向き（τ > 0.4）: +10
    """
    pass
```

#### C. 事業の安定性（20点）
```python
def calculate_stability_score(
    sales: list[float],
    operating_income: list[float]
) -> int:
    """
    - 売上増加年が3年以上: +10
    - 営業利益増加年が3年以上: +10
    """
    pass
```

#### D. 収益性の維持（20点）
```python
def calculate_profitability_score(
    operating_margins: list[float]
) -> int:
    """
    - 前年差マイナスが2回以下: +10
    - −2.0pt以上の低下が2年連続でない: +10
    """
    pass
```

### 7.3 トレンド計算（Kendallのτ）

```python
def calculate_kendall_tau(values: list[float]) -> float:
    """
    Kendallの順位相関係数を計算
    scipy.stats.kendalltau を使用
    """
    from scipy.stats import kendalltau
    years = list(range(len(values)))
    tau, p_value = kendalltau(years, values)
    return tau
```

---

## 8. 実装順序（推奨）

### Phase 1: データ基盤（完了）
- [x] EdinetProfitAndLoss モデル/リポジトリ
- [x] EdinetCashFlowStatement モデル/リポジトリ
- [x] EdinetStockDividend モデル/リポジトリ
- [x] 財務データ取得処理（同期実行）

### Phase 2: 財務分析サービス
1. FinancialAnalysisService 実装
   - 配当履歴取得
   - EPS履歴取得
   - 営業CF履歴取得
   - トレンド計算（Kendallのτ）
   - 営業利益率計算
2. ユニットテスト作成

### Phase 3: スクリーニング機能
1. ScreeningResult モデル/リポジトリ作成
2. ScreeningService 実装
   - 必須条件チェック
   - スコア計算
3. スクリーニングAPI作成
4. 統合テスト作成
5. 処理（同期実行）作成

### Phase 4: 監視リスト機能
1. WatchList モデル/リポジトリ作成
2. WatchListService 実装
3. 株価更新処理（同期実行）作成
4. 監視リストAPI作成
5. フロントエンド画面作成



---

## 9. 外部ライブラリ

### 既存
- `yfinance`: Yahoo Finance APIから株価取得
- `pandas`: データ処理
- `numpy`: 数値計算

### 追加候補
- `scipy`: 統計計算（Kendallのτ計算）

```bash
poetry add scipy
```

---

## 10. フロントエンド画面イメージ

### 10.1 スクリーニング結果画面
- スクリーニング実行日
- 評価銘柄数、通過銘柄数
- スコア順のテーブル表示
- フィルター機能（スコア範囲、ステータス）

### 10.2 監視リスト画面
- 監視銘柄一覧
- 現在株価、配当利回り
- 監視レベルのバッジ表示
- 購入候補のハイライト

### 10.3 判断履歴画面
- 実行済み/未実行のフィルター

---

## 11. 注意事項

### 11.1 データ整合性
- 財務データは年度単位で完全性を担保する
- 欠損データがある場合は、その銘柄をスクリーニング対象外とする

### 11.2 パフォーマンス
- スクリーニングは全銘柄（4000+）を対象とするため、非同期処理を活用
- 処理でキャッシュを活用（計算結果のメモ化）

### 11.3 拡張性
- セクター別補正ルールは、後から追加できる設計とする
- 評価指標の追加（ネットキャッシュ、ROIC等）に対応可能な構造

---

説明: 設計書の「ファイル構成」セクションを、実際のリポジトリ内ディレクトリ (`app/api/v1`, `app/services/core`, `app/services/market_data`, `app/repositories`, `scripts/batch` など) に合わせて更新しました。

変更点のポイント:
- `app/api/v1` にある既存のルーター（`edinet.py`, `stock_price.py`, `stock_master.py`, `accounts.py`, `auth.py` 等）を反映
- `app/services` の再編（`core` と `market_data` サブパッケージ）に合わせてサービスの配置例を整理
- バッチスクリプトは `scripts/batch` 配下にある実ファイル名を参照する形に更新

（必要なら続けて、実際のファイルで未作成のモデル・リポジトリ雛形を追加します。）
