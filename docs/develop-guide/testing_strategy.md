category: develop-guide
ai_context: high
last_updated: 2026-03-02
related_docs:
	- ../develop-guide/development-workflow.md

# テスト戦略

本プロジェクトでは、**Unit Test（単体テスト）**・**Integration Test（統合テスト）**・**E2E Test（エンドツーエンドテスト）** の3階層テストを実施します。

## テストレベルの定義

### Unit Test（`tests/unit/`）

**目的**: 関数・クラスメソッドが独立して正常に機能することを確認。

**特徴**:
- 外部依存（DB、外部API）はモック化
- 高速実行
- 開発時に頻繁に実行

**必須ルール**:
- **ファイル命名規約**: `test_<ソース名>.py`
  例: `app/services/stock_service.py` → `tests/unit/services/test_stock_service.py`
- **ディレクトリ構造**: app配下の構造をそのまま反映
- **自動チェック**: `scripts/hooks/check_unit_test_coverage.py` で命名規約と存在確認を実施

**チェック対象外**:
- `__init__.py`, `main.py`, `templates_config.py` のテストは不要
- `static/`, `templates/`, `__pycache__/` は対象外

### Integration Test（`tests/integration/`）

**目的**: 複数レイヤー間の連携が正常に機能することを確認。

**対象例**:
- API層 ↔ Services層
- Services層 ↔ Repositories層
- 実DB操作とスキーマの整合性
- 外部API（Yahoo Finance等）の連携

**特徴**:
- テスト用DBを使用
- トランザクションロールバック or データクリーンアップで後処理
- 命名規約なし（自由度あり）

### E2E Test（`tests/e2e/`）

**目的**: ユーザーシナリオを通じてシステム全体の動作を検証。

**⚠️ このプロジェクトの E2E テスト特有の方針**:
本プロジェクトの E2E テストでは、**実際の外部API（Yahoo Finance、EDINET等）を呼び出し、実データをダウンロードして DB に格納できることを確認する** ことが重要です。単なるモック検証ではなく、実装全体の連携と実データの永続化を検証します。そのため、実行時間が長くなることは許容されます。

**特徴**:
- 実データベースを使用
- **実外部API呼び出し**（Yahoo Finance、EDINET等からの実データ取得）
- **実データの DB 永続化確認**（取得したデータが正確に DB に格納されることを検証）
- FastAPI を `TestClient` でインプロセス実行
- テスト前にマイグレーション実施済みの前提
- 時間がかかってもよい（実API呼び出しのため）

# tests/e2e/conftest.py での到達性チェック例

```python
def is_db_reachable():
    try:
        engine = sqlalchemy.create_engine(DB_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

def pytest_collection_modifyitems(config, items):
    if not is_db_reachable():
        skip_marker = pytest.mark.skip(reason="DB unreachable")
        for item in items:
            if "e2e" in str(item.fspath):
                item.add_marker(skip_marker)
```

## テストコード作成時に守るべきルール

| ✅ すべき / ✅ OK                                 | ❌ してはいけない                             |
| ----------------------------------------------- | -------------------------------------------- |
| 外部APIはモック化（UnitTest）                   | テスト間でデータを共有                       |
| AAA パターン: Arrange → Act → Assert            | 複数の動作を1テストで検証                    |
| テストケース名で何をテストするか明確に          | テスト実装の詳細に依存したテスト             |
| Fixture で共通セットアップを集約（conftest.py） | テストのためだけのプロダクションコード       |
| テスト後は必ずクリーンアップ                    | 時刻依存処理を直接使用（datetime.now()など） |
| テスト間で独立したデータを使用                  | テストの実行順序に依存                       |

## テスト関数の命名規則

```python
# ✅ 推奨形式
def test_機能名_条件_期待結果():
    """説明"""
    pass

# 例
def test_create_stock_with_valid_data_returns_success():
    """正常なデータで株式を作成すると成功を返す"""
    pass

def test_get_stock_price_when_not_found_raises_exception():
    """株価が見つからない場合は例外を発生させる"""
    pass

# グループ化する場合
class TestStockService:
    def test_create_success(self):
        pass

    def test_invalid_code_raises_error(self):
        pass
```

## テストデータ・Fixture の配置

```
tests/
├── conftest.py                    # 全テスト共通
├── unit/
│   ├── conftest.py                # unit テスト共通
│   ├── services/
│   │   ├── test_stock_service.py
│   │   └── conftest.py            # services テスト専用
│   └── repositories/
├── integration/
│   └── conftest.py
├── e2e/
│   ├── conftest.py
│   └── utils.py                   # E2E 用ヘルパー関数集約
└── fixtures/
    └── sample_data.json
```

## テスト実行

```bash
# 全テスト実行
poetry run pytest

# Unit Test のみ
poetry run pytest tests/unit/

# Integration Test のみ
poetry run pytest tests/integration/

# E2E Test のみ
poetry run pytest tests/e2e/

# カバレッジ測定
poetry run pytest --cov=app tests/unit/

# Unit Test 命名規約チェック（CI で自動実行）
python scripts/hooks/check_unit_test_coverage.py
```

## 参考資料

- テスト命名規約チェック: [scripts/hooks/check_unit_test_coverage.py](../../scripts/hooks/check_unit_test_coverage.py)
- E2E テスト実行前提: [tests/e2e/conftest.py](../../tests/e2e/conftest.py)
