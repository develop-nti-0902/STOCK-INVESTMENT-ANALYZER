# E2E テスト ガイド

E2E（End-to-End）テスト は、アプリケーション全体の統合動作を確認するテストです。このディレクトリのテストは、**実際の HTTP API 呼び出し** + **DB 統合** を検証します。

---

## テストコンベンション

### マーク

すべてのファイルで `@pytest.mark.xdist_group("e2e")` を使用し、並列実行グループを分離してください。

```python
@pytest.mark.xdist_group("e2e")
class TestExample:
    def test_something(self):
        pass
```

### DB 隔離

E2E テストは test-specific DB を使用します。各テスト後に自動的にクリーンアップされます。

---

## スクリーニング API E2E テスト

### 概要

`POST /api/v1/screening/run` エンドポイントの完全な E2E テスト。過去 5 年分の EDINET 疑似データを CSV から投入し、スクリーニング結果の正確性を検証します。

### テストファイル

- **テストコード**: [test_screening_run_e2e.py](./test_screening_run_e2e.py)
- **CSV データ**: `fixtures/data/edinet_*.csv` × 4 ファイル
- **検証ヘルパー**: [screening_assertions.py](./screening_assertions.py)
- **データローダー**: [csv_data_loader.py](./csv_data_loader.py)
- **Fixture**: [conftest.py](./conftest.py) の `loaded_edinet_test_data`

### テストケース一覧

| #   | テスト名                                         | 説明                           | 検証項目                   |
| --- | ------------------------------------------------ | ------------------------------ | -------------------------- |
| 1   | `test_screening_run_returns_200_with_valid_data` | API が 200 レスポンス返却      | HTTP ステータスコード      |
| 2   | `test_screening_run_response_schema_valid`       | レスポンスのスキーマが準拠     | JSON 構造（status/result） |
| 3   | `test_screening_run_saves_results_to_db`         | 結果が DB に保存               | screening_results テーブル |
| 4   | `test_screening_run_with_specific_sec_codes`     | 特定銘柄でフィルタ実行         | パラメータ処理             |
| 5   | `test_screening_run_with_evaluation_date`        | 異なる評価日でのスクリーニング | 日付パラメータ             |
| 6   | `test_screening_results_financial_validity`      | スコアが妥当範囲               | 財務項目の検証             |
| 7   | `test_screening_run_response_with_all_params`    | 複数パラメータでの実行         | パラメータ組み合わせ       |
| 8   | `test_screening_results_sorted_by_score`         | 結果がスコアでソート済み       | 降順ソート確認             |
| 9   | `test_screening_run_contains_eligible_stocks`    | 適格銘柄が含まれている         | 結果 count                 |
| 10  | `test_screening_run_performance`                 | 実行時間が <10s                | パフォーマンス             |

### 実行方法

**全テスト実行**:
```bash
poetry run pytest tests/e2e/test_screening_run_e2e.py -v
```

**特定テスト実行**:
```bash
poetry run pytest tests/e2e/test_screening_run_e2e.py::TestScreeningRunE2E::test_screening_run_returns_200_with_valid_data -v
```

**カバレッジ計測**:
```bash
poetry run pytest tests/e2e/test_screening_run_e2e.py --cov=app.services.screening --cov-report=html
```

### 期待される実行結果

```
======================== 10 passed in 32.43s ========================
```

- **テスト数**: 10 個
- **実行時間**: 約 32.43 秒
- **平均テスト実行時間**: 3.2 秒/テスト

### データ準備（Fixture）

### `loaded_edinet_test_data` Fixture

各テスト前に自動的に疑似データを投入します：

1. **既存データをクリア** - 3 つの EDINET テーブルと銘柄マスタが初期化
2. **CSV 読み込み** - 4 つの CSV ファイルから異なるデータを投入
3. **テスト実行** - API 呼び出しと結果検証
4. **自動クリーンアップ** - テスト終了後にロールバック

**投入される疑似データ**:

| テーブル                   | 銘柄数 | 年度数 | 合計レコード |
| -------------------------- | ------ | ------ | ------------ |
| stock_master               | 5      | -      | 5            |
| edinet_profit_and_loss     | 5      | 5      | 25           |
| edinet_cash_flow_statement | 5      | 5      | 25           |
| edinet_stock_dividend      | 5      | 5      | 25           |

### CSV データファイル

詳細な管理方法は [docs/testing/csv_maintenance.md](../../docs/testing/csv_maintenance.md) を参照してください。

---

## トラブルシューティング

### DB 接続エラー

```
ERROR: DB unreachable — skipping E2E tests
```

**原因**: `DATABASE_URL` が設定されていない

**解決**:
```bash
# .env ファイルを確認
cat .env | grep DATABASE_URL

# SQLite テスト DB を明示的に指定
export DATABASE_URL="sqlite:///F:/path/to/test.db"
poetry run pytest tests/e2e/test_screening_run_e2e.py -v
```

### CSV パースエラー

```
ValueError: CSV ファイルが見つかりません: tests/e2e/fixtures/data/edinet_profit_and_loss_5yr.csv
```

**原因**: CSV ファイルが見つからない

**解決**:
```bash
# ファイルの存在確認
ls -la tests/e2e/fixtures/data/

# 相対パスが正しいか確認（プロジェクトルートから実行）
pwd  # プロジェクトルートであることを確認
```

### タイムアウト

```
TimeoutError: Test took longer than 10s
```

**原因**: DB クエリが遅い

**解決**:
```bash
# DB を確認
poetry run sqlite3 F:/path/to/test.db ".schema"

# インデックスが正しく設定されているか確認
poetry run sqlite3 F:/path/to/test.db ".indexes"
```

### テストが FAIL

```
AssertionError: screening_results is None
```

**原因**: スクリーニング結果が返却されていない

**解決**:
```bash
# テスト用 API endpoint を手動で呼び出し
poetry run python -c "
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
response = client.post('/api/v1/screening/run?evaluation_date=2025-03-31')
print(f'Status: {response.status_code}')
print(f'Body: {response.json()}')
"
```

---

## CI/CD 統合

### GitHub Actions での実行

`.github/workflows/e2e-tests.yml` に以下を追加：

```yaml
name: E2E Tests

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.14"

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install

      - name: Run E2E tests
        run: poetry run pytest tests/e2e/test_screening_run_e2e.py -v --tb=short
        env:
          DATABASE_URL: "sqlite:///test.db"

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### ローカルでの実行確認

```bash
# Lint チェック
poetry run pytest tests/e2e/ --lint

# テスト実行
poetry run pytest tests/e2e/test_screening_run_e2e.py -v -x

# カバレッジ付き実行
poetry run pytest tests/e2e/test_screening_run_e2e.py --cov --cov-report=html
```

---

## ベストプラクティス

### 1. Fixture 設計

- **スコープ**: `function` スコープを推奨（各テストが独立）
- **クリーンアップ**: SQL ロールバックで自動クリーンアップ
- **パラメータ化**: `@pytest.mark.parametrize` で複数パターン検証

### 2. アサーション

- **検証ヘルパー**: [screening_assertions.py](./screening_assertions.py) の メソッドを利用
- **メッセージ**: アサーション失敗時は 詳細メッセージを含める
  ```python
  assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
  ```

### 3. パフォーマンス

- **目標実行時間**: 単一テスト < 5s、全テスト < 60s
- **並列実行**: `pytest-xdist` で複数ワーカで実行
  ```bash
  poetry run pytest tests/e2e/ -n auto
  ```

### 4. DB 隔離

- **テーブルクリア**: 各テスト前に DELETE で確実にクリア
- **トランザクション**: `AsyncSession.begin/rollback()` で囲む
- **複製キー対応**: 一意制約エラー時は スキップ

---

## 参考資料

- **CSV メンテナンス**: [docs/testing/csv_maintenance.md](../../docs/testing/csv_maintenance.md)
- **スクリーニング API**: [app/api/v1/screening.py](../../app/api/v1/screening.py)
- **スクリーニングサービス**: [app/services/screening/screening_service.py](../../app/services/screening/screening_service.py)
- **テスト戦略全般**: [docs/develop-guide/testing_strategy.md](../../docs/develop-guide/testing_strategy.md)

---

**更新履歴**: 2026-03-05 E2E スクリーニングテスト セクション追加
