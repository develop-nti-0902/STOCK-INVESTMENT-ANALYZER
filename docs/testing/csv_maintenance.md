# E2E テスト用 CSV メンテナンスガイド

**主要な目的**: POST /api/v1/screening/run E2E テストで使用する疑似 EDINET データの管理・保守

---

## 1. CSV ファイル一覧

E2E テストは以下 4 つの CSV ファイルから疑似データを投入します：

| ファイル名                             | パス                       | テーブル名                   | 行数（含ヘッダ） | 用途                     |
| -------------------------------------- | -------------------------- | ---------------------------- | ---------------- | ------------------------ |
| **stock_master_screening.csv**         | `tests/e2e/fixtures/data/` | `stock_master`               | 6                | 5 銘柄 + ヘッダ          |
| **edinet_profit_and_loss_5yr.csv**     | `tests/e2e/fixtures/data/` | `edinet_profit_and_loss`     | 26               | 5 銘柄 × 5 年度 + ヘッダ |
| **edinet_cash_flow_statement_5yr.csv** | `tests/e2e/fixtures/data/` | `edinet_cash_flow_statement` | 26               | 5 銘柄 × 5 年度 + ヘッダ |
| **edinet_stock_dividend_5yr.csv**      | `tests/e2e/fixtures/data/` | `edinet_stock_dividend`      | 26               | 5 銘柄 × 5 年度 + ヘッダ |

---

## 2. スキーマ定義

### 2.1 stock_master（銘柄マスタ）

```
カラム名               型          制約              説明
─────────────────────────────────────────────────────
stock_code           VARCHAR     PRIMARY KEY       銘柄コード（4桁）
symbol               VARCHAR     UNIQUE            証券シンボル
stock_name           VARCHAR     NOT NULL          銘柄名
industry_code        VARCHAR                       産業分類コード
market_capitalization DECIMAL(18,2)               時価総額（万円）
is_active            BOOLEAN     DEFAULT=true      アクティブフラグ
```

**サンプル**:
```csv
stock_code,symbol,stock_name,industry_code,market_capitalization,is_active
1001,1001,Growth Inc,1000,500000000,1
1002,1002,High Dividend Corp,1100,400000000,1
1003,1003,Quality Ltd,1200,600000000,1
2001,2001,Declining Inc,2000,300000000,1
2002,2002,Recovery Co,2100,250000000,1
```

---

### 2.2 edinet_profit_and_loss（利益・損失）

```
カラム名                    型              制約            説明
──────────────────────────────────────────────────────
doc_id                     VARCHAR         PRIMARY KEY    文書 ID（SYYYYXXXXXX形式）
sec_code                   VARCHAR         NOT NULL       証券コード（4桁）
submission_date            DATE            NOT NULL       提出日（YYYY-MM-DD）
period_end_date            DATE            NOT NULL       期末日（YYYY-MM-DD）
fiscal_year                INTEGER         NOT NULL       会計年度（YYYY）
report_type                VARCHAR         NOT NULL       報告書タイプ（annual等）
net_sales                  DECIMAL(18,2)   NOT NULL       売上高（百万円）
operating_income           DECIMAL(18,2)   NOT NULL       営業利益（百万円）
eps                        DECIMAL(18,2)   NOT NULL       1株当たり利益（円）
candidate_contexts         VARCHAR                        XBRL コンテキスト
candidate_keys             VARCHAR                        XBRL キー
is_consolidated            BOOLEAN         DEFAULT=true   連結フラグ
```

**サンプルデータの生成ルール**:

| パターン       | 銘柄       | YoY 成長率 | 説明                             |
| -------------- | ---------- | ---------- | -------------------------------- |
| **成長企業**   | 1001, 1003 | +10%       | 年度ごとに 10% の成長            |
| **高配当企業** | 1002       | +10%       | 重点は配当だが売上成長もあり     |
| **衰退企業**   | 2001       | -5%        | 年度ごとに 5% 低下               |
| **回復企業**   | 2002       | V字        | FY21 → FY23 低下、FY24～以降回復 |

**計算例（銘柄 1001）**:
```
FY21: net_sales = 2500
FY22: net_sales = 2500 × 1.10 = 2750
FY23: net_sales = 2750 × 1.10 = 3025
FY24: net_sales = 3025 × 1.10 = 3327.50
FY25: net_sales = 3327.50 × 1.10 = 3660.25

EPS の計算: EPS = net_sales × 0.10（仮の係数）
FY21: eps = 2500 × 0.10 = 250
FY25: eps = 3660.25 × 0.10 = 366.025 → 366.03（小数2桁で丸め）
```

---

### 2.3 edinet_cash_flow_statement（キャッシュフロー）

```
カラム名                    型              制約            説明
──────────────────────────────────────────────────────
doc_id                     VARCHAR         PRIMARY KEY    文書 ID
sec_code                   VARCHAR         NOT NULL       証券コード
submission_date            DATE            NOT NULL       提出日
period_end_date            DATE            NOT NULL       期末日
fiscal_year                INTEGER         NOT NULL       会計年度
report_type                VARCHAR         NOT NULL       報告書タイプ
operating_cf               DECIMAL(18,2)   NOT NULL       営業CF（百万円）
[その他 CF 関連項目]                                       ※ テーブル定義に準拠
```

**生成ルール**:
```
operating_cf = net_sales × 0.40 ~ 0.60（売上の 40-60%）
```

**計算例（銘柄 1001）**:
```
FY21: net_sales = 2500, operating_cf = 2500 × 0.50 = 1250
FY25: net_sales = 3660.25, operating_cf = 3660.25 × 0.50 = 1830.13
```

**制約**: `operating_cf >= 0` （負値は許可しない）

---

### 2.4 edinet_stock_dividend（配当）

```
カラム名                    型              制約            説明
──────────────────────────────────────────────────────
doc_id                     VARCHAR         PRIMARY KEY    文書 ID
sec_code                   VARCHAR         NOT NULL       証券コード
submission_date            DATE            NOT NULL       提出日
period_end_date            DATE            NOT NULL       期末日
fiscal_year                INTEGER         NOT NULL       会計年度
report_type                VARCHAR         NOT NULL       報告書タイプ
dividend_actual            DECIMAL(18,2)   NOT NULL       実績配当（円/株）
dividend_adj               DECIMAL(18,2)   NOT NULL       調整後配当（円/株）
[その他配当関連項目]                                       ※ テーブル定義に準拠
```

**配当パターン（著 sec_code）**:

| 銘柄   | パターン | 説明             | 値                    |
| ------ | -------- | ---------------- | --------------------- |
| 1002   | 高配当   | EPS の 30-40%    | FY21: 45, FY25: 66    |
| 1003   | 標準配当 | EPS の 20-25%    | FY21: 70, FY25: 128.6 |
| その他 | 段階的   | 年度ごとに 5-10% | 段階的に増加          |

**制約**: `dividend_adj >= 0` （負値は許可しない）

---

## 3. データ生成ルール

### 3.1 証券コード（sec_code）

- **4 桁の数字** （例: 1001, 1002, 2001）
- **ユニーク** - 各銘柄は 1 つのコードのみ
- **stock_master テーブルに存在** - 必須

### 3.2 文書 ID（doc_id）

形式: `S{YYYY}{XXXXXX}`

```
S2021000001  → FY 2021, 001 番目の文書
S2022000002  → FY 2022, 002 番目の文書
S2025000005  → FY 2025, 005 番目の文書
```

**採番ルール**:
```python
doc_id = f"S{fiscal_year}{str(index).zfill(6)}"
# FY 2025 の 5 番目の記録 → S2025000005
```

### 3.3 日付（date カラム）

- **形式**: `YYYY-MM-DD` （ISO 8601）
- **期末日（period_end_date）**: 各会計年度の 3 月 31 日
  ```
  FY2021 → 2021-03-31
  FY2022 → 2022-03-31
  ...
  FY2025 → 2025-03-31
  ```
- **提出日（submission_date）**: 期末日の 3 ヶ月後（6 月 30 日）
  ```
  FY2021 → 2021-06-30
  FY2022 → 2022-06-30
  ...
  ```

### 3.4 数値（Decimal 型）

- **精度**: 小数点以下 2 桁（金融データの標準）
  ```
  2500.00
  3660.25
  1830.13
  ```
- **正値制約**: 営業 CF、配当は >= 0

### 3.5 Boolean 型

- **CSV 表記**: `1` = true、`0` = false
  ```
  is_active=1    → is_active=True
  is_consolidated=1 → is_consolidated=True
  ```

---

## 4. テーブル構造変更時の修正手順

### 4.1 新規カラムの追加

**例**: `edinet_profit_and_loss` に `gross_profit` カラムを追加する場合

1. **アプリ層の DB 定義を更新**
   - [app/models/market_data/edinet/edinet_profit_and_loss.py](../../app/models/market_data/edinet/edinet_profit_and_loss.py)
   - 新規カラムを追加

2. **Alembic マイグレーション生成**
   ```bash
   poetry run alembic revision --autogenerate -m "Add gross_profit to edinet_profit_and_loss"
   ```

3. **CSV ファイル更新**
   - `edinet_profit_and_loss_5yr.csv` にヘッダと値を追加
   - 値の生成ルールを本ドキュメントに記載

4. **EdinetCsvDataLoader の型変換確認**
   - 新規カラムに対する型変換ロジック（Decimal, INTEGER, DATE 等）が自動で処理されるか確認
   - [tests/e2e/csv_data_loader.py](../../tests/e2e/csv_data_loader.py) の `_convert_row_types` メソッドを確認

5. **テスト実行**
   ```bash
   poetry run pytest tests/e2e/test_screening_run_e2e.py -v
   ```

### 4.2 カラム名の変更

**例**: `period_end_date` → `fiscal_period_end_date` に変更する場合

1. **アプリ層の DB 定義を更新** - モデル定義のカラム名を変更
2. **Alembic マイグレーション** - カラム名を更新
3. **CSV ファイルのヘッダを変更**
   ```csv
   period_end_date → fiscal_period_end_date
   ```
4. **EdinetCsvDataLoader** - 自動的に新カラム名で処理される（マッピングが汎用）

### 4.3 カラムの削除

1. **アプリ層から削除宣言**
2. **Alembic マイグレーション実行**
3. **CSV ファイルからカラムを削除**
4. **テスト実行** - エラーがないか確認

---

## 5. CSV エンコーディング注意点

### 5.1 必須: UTF-8 no-BOM

すべての CSV ファイルは **UTF-8 no-BOM** でエンコードされている必要があります。

```bash
# ファイルのエンコーディング確認（Windows）
file -b --mime-encoding edinet_profit_and_loss_5yr.csv
# 出力: utf-8
```

### 5.2 Excel での保存方法

Excel で CSV ファイルを修正する場合：

1. **ファイルを開く** - Excel で `edinet_profit_and_loss_5yr.csv` を開く
2. **編集** - 値を変更
3. **「名前を付けて保存」を選択**
4. **ファイル形式**: `CSV (コンマ区切り)` を指定
5. **エンコーディング**: UTF-8 に設定（デフォルト）
6. **保存** - BOM なしで保存される

**注意**: Excel は BOM を付けることがあるため、保存後に検証を推奨

### 5.3 エンコーディング検証

```bash
# Python で BOM 確認
python -c "
import pathlib
p = pathlib.Path('edinet_profit_and_loss_5yr.csv')
data = p.read_bytes()
has_bom = data.startswith(b'\xef\xbb\xbf')
print('BOM present:', has_bom)
"
```

---

## 6. サンプル追加・削除方法

### 6.1 新規銘柄を追加する場合

**例**: 新しい成長企業 `1004` を追加する場合

**手順**:

1. **stock_master に追加**
   ```csv
   1004,1004,New Growth Co,1300,550000000,1
   ```

2. **P&L CSV に 5 年度分データを追加**
   ```csv
   S2021000006,1004,2021-06-30,2021-03-31,2021,annual,2800.00,420.00,280.00,CurrentYearDuration_JP,jpFY21,true
   S2022000006,1004,2022-06-30,2022-03-31,2022,annual,3080.00,462.00,308.00,CurrentYearDuration_JP,jpFY22,true
   S2023000006,1004,2023-06-30,2023-03-31,2023,annual,3388.00,508.20,338.80,CurrentYearDuration_JP,jpFY23,true
   S2024000006,1004,2024-06-30,2024-03-31,2024,annual,3726.80,558.90,372.68,CurrentYearDuration_JP,jpFY24,true
   S2025000006,1004,2025-06-30,2025-03-31,2025,annual,4099.48,614.78,409.95,CurrentYearDuration_JP,jpFY25,true
   ```
   - **doc_id**: `S{YYYY}{次のインデックス}`（例: S2021000006）
   - **パターン**: +10% YoY 成長を想定
   - **EPS = net_sales × 0.10**

3. **CF CSV に追加**
   ```csv
   S2021000006,1004,2021-06-30,2021-03-31,2021,annual,1400.00,...
   S2022000006,1004,2022-06-30,2022-03-31,2022,annual,1540.00,...
   ...
   ```
   - **operating_cf = net_sales × 0.50**

4. **Dividend CSV に追加**
   ```csv
   S2021000006,1004,2021-06-30,2021-03-31,2021,annual,84.00,84.00,...
   S2022000006,1004,2022-06-30,2022-03-31,2022,annual,92.40,92.40,...
   ...
   ```
   - **dividend_adj = eps × 0.30**（高配当パターン）

5. **テスト実行**
   ```bash
   poetry run pytest tests/e2e/test_screening_run_e2e.py -v -k test_screening
   ```

### 6.2 既存銘柄を削除する場合

**例**: 銘柄 `1002` を削除する場合

1. **すべての CSV ファイルから該当銘柄の行を削除**
   - stock_master（1 行）
   - edinet_profit_and_loss_5yr.csv（5 行）
   - edinet_cash_flow_statement_5yr.csv（5 行）
   - edinet_stock_dividend_5yr.csv（5 行）

2. **テスト実行** - 関連するテストが失敗しないか確認
   ```bash
   poetry run pytest tests/e2e/test_screening_run_e2e.py::TestScreeningRunE2E::test_screening_with_specific_sec_codes -v
   ```

---

## 7. バリデーション確認コマンド

### 7.1 CSV 形式チェック

```bash
# Python で CSV パース確認
python -c "
import csv
from pathlib import Path

csv_files = [
    'tests/e2e/fixtures/data/stock_master_screening.csv',
    'tests/e2e/fixtures/data/edinet_profit_and_loss_5yr.csv',
    'tests/e2e/fixtures/data/edinet_cash_flow_statement_5yr.csv',
    'tests/e2e/fixtures/data/edinet_stock_dividend_5yr.csv',
]

for csv_file in csv_files:
    p = Path(csv_file)
    with open(p) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f'{p.name}: {len(rows)} data rows')
        if rows:
            print(f'  Columns: {list(rows[0].keys())}')
"
```

### 7.2 財務整合性チェック

```bash
# EPS < net_sales の確認
python -c "
import csv
from decimal import Decimal
from pathlib import Path

path = Path('tests/e2e/fixtures/data/edinet_profit_and_loss_5yr.csv')
with open(path) as f:
    reader = csv.DictReader(f)
    for row in reader:
        eps = Decimal(row['eps'])
        net_sales = Decimal(row['net_sales'])
        if eps > net_sales:
            print(f'ERROR: {row[\"sec_code\"]} EPS {eps} > net_sales {net_sales}')
        else:
            print(f'OK: {row[\"sec_code\"]} {eps} <= {net_sales}')
"
```

### 7.3 E2E テスト実行

```bash
# 全 E2E テスト実行
poetry run pytest tests/e2e/test_screening_run_e2e.py -v

# 特定テスト実行
poetry run pytest tests/e2e/test_screening_run_e2e.py::TestScreeningRunE2E::test_screening_run_returns_200_with_valid_data -v

# カバレッジ計測
poetry run pytest tests/e2e/test_screening_run_e2e.py --cov=app.services.screening --cov-report=term-missing -q
```

---

## 8. 既知の制限事項とベストプラクティス

### 8.1 複製キー（Duplicate Keys）

同じ `sec_code` × `period_end_date` × `report_type` の組み合わせで複数レコードがある場合、DB 投入時にエラーになります。

**対応**: EdinetCsvDataLoader は 1 行ずつ再試行して、スキップします。

### 8.2 NULL vs 0

CSV では空白値は `NULL` に変換されます。数値型の 0 と区別されません。

```csv
operating_cf =       # NULL
operating_cf = 0     # 0
```

### 8.3 エンコーディング的な問題

Excel で保存する際は、BOM が付属しないことを確認してください。

```bash
# BOM 削除（必要に応じて）
python -c "
import pathlib
p = pathlib.Path('edinet_profit_and_loss_5yr.csv')
data = p.read_text(encoding='utf-8-sig')
p.write_text(data, encoding='utf-8')
"
```

---

## 9. トラブルシューティング

| 問題                                              | 原因                            | 解決                               |
| ------------------------------------------------- | ------------------------------- | ---------------------------------- |
| `FileNotFoundError: CSV ファイルが見つかりません` | CSV パスが間違っている          | パスを確認、相対パスで表記         |
| `ValueError: EPS > net_sales`                     | 財務データが不整合              | CSV を修正、EPS < net_sales を確保 |
| `UnicodeDecodeError`                              | エンコーディングが UTF-8 でない | Excel で UTF-8 no-BOM で再保存     |
| `テストが FAIL`                                   | DB のテーブル構造が古い         | Alembic マイグレーション実行       |
| BOM 付きの CSV で エラー                          | Excel が BOM を付けた           | Python スクリプトで BOM 削除       |

---

## 10. リソース

- **テストファイル**: [tests/e2e/test_screening_run_e2e.py](../../tests/e2e/test_screening_run_e2e.py)
- **CSV ローダー**: [tests/e2e/csv_data_loader.py](../../tests/e2e/csv_data_loader.py)
- **Fixture定義**: [tests/e2e/conftest.py](../../tests/e2e/conftest.py)
- **検証ヘルパー**: [tests/e2e/screening_assertions.py](../../tests/e2e/screening_assertions.py)

---

**更新履歴**: 2026-03-05 初版
