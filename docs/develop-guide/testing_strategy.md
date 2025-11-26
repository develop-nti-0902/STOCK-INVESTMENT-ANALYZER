category: develop-guide
ai_context: high
last_updated: 2025-11-26
related_docs:
	- ../standards/testing-standards.md
	- ../develop-guide/development-workflow.md
	- ../architecture/architecture_overview.md

# テスト戦略

## 目次
- [テスト戦略](#テスト戦略)
  - [目次](#目次)
  - [1. 概要](#1-概要)
  - [2. テストレベルの定義](#2-テストレベルの定義)
    - [2.1 単体テスト（Unit Test）](#21-単体テストunit-test)
    - [2.2 統合テスト（Integration Test）](#22-統合テストintegration-test)
    - [2.3 E2Eテスト（End-to-End Test）](#23-e2eテストend-to-end-test)
  - [3. テストピラミッド](#3-テストピラミッド)
  - [4. テスト対象とカバレッジ目標](#4-テスト対象とカバレッジ目標)
  - [5. テストツールとフレームワーク](#5-テストツールとフレームワーク)
  - [6. テストファイル命名規約](#6-テストファイル命名規約)
    - [6.1 ファイル名の規則](#61-ファイル名の規則)
    - [6.2 ディレクトリ構造](#62-ディレクトリ構造)
    - [6.3 テスト関数の命名規則](#63-テスト関数の命名規則)
    - [6.4 テストクラスの命名規則](#64-テストクラスの命名規則)
    - [6.5 Fixtureファイルの命名](#65-fixtureファイルの命名)
    - [6.6 テストデータファイルの命名](#66-テストデータファイルの命名)
  - [7. テストデータ管理](#7-テストデータ管理)
  - [8. モックとスタブの使用方針](#8-モックとスタブの使用方針)
  - [9. テストコード品質の維持](#9-テストコード品質の維持)
  - [10. ベストプラクティス](#10-ベストプラクティス)


## 1. 概要
本ドキュメントは、STOCK-INVESTMENT-ANALYZERプロジェクトにおけるテスト戦略を定義します。品質保証、リグレッション防止、保守性向上を目的とし、開発フローに組み込むべきテストの種類、範囲、実行タイミングを明確化します。

## 2. テストレベルの定義

### 2.1 単体テスト（Unit Test）
**目的**: 個々の関数・クラス・メソッドが仕様通りに動作することを確認する。

**対象**:
- Services層のビジネスロジック
- Repositories層のデータアクセスロジック
- Utils/Helpers層の汎用関数
- Schemas/バリデーションロジック

**特徴**:
- 外部依存（DB、外部API）はモック化
- 高速に実行可能
- 開発者が頻繁に実行
- カバレッジ目標: 80%以上

**実装ディレクトリ**: `tests/unit/`

### 2.2 統合テスト（Integration Test）
**目的**: 複数のコンポーネント間の連携動作を確認する。

**対象**:
- API層とServices層の連携
- Services層とRepositories層の連携
- データベーススキーマの整合性
- 外部APIとの連携（必要に応じて）

**特徴**:
- テスト用DBを使用
- トランザクションロールバックでクリーンアップ
- 実際のDB接続を行う
- カバレッジ目標: 主要フロー70%以上

**実装ディレクトリ**: `tests/integration/`

### 2.3 E2Eテスト（End-to-End Test）
**目的**: ユーザーの実際の操作フローをシミュレートし、システム全体の動作を確認する。

**対象**:
- 主要なユーザーシナリオ
- 画面遷移フロー
- フロントエンドとバックエンドの統合動作

**特徴**:
- ブラウザ自動化ツールを使用
- テスト環境での実行
- 実行時間が長い
- カバレッジ目標: クリティカルパス100%

**実装ディレクトリ**: `tests/e2e/`

## 3. テストピラミッド
本プロジェクトでは、以下のテストピラミッドに従います：

```
        /\
       /E2E\      少数・遅い・高コスト
      /------\
     /統合テスト\   中程度
    /----------\
   /  単体テスト  \  多数・高速・低コスト
  /--------------\
```

**比率目安**:
- 単体テスト: 70%
- 統合テスト: 20%
- E2Eテスト: 10%

## 4. テスト対象とカバレッジ目標

| レイヤー     | カバレッジ目標 | 優先度 | 備考                   |
| ------------ | -------------- | ------ | ---------------------- |
| Services     | 90%以上        | 最高   | ビジネスロジックの中核 |
| Repositories | 80%以上        | 高     | データアクセスの信頼性 |
| API          | 80%以上        | 高     | エンドポイントの網羅   |
| Utils        | 85%以上        | 高     | 汎用関数の正確性       |
| Schemas      | 75%以上        | 中     | バリデーションの確認   |
| Exceptions   | 60%以上        | 中     | エラーハンドリング     |

## 5. テストツールとフレームワーク

**Pythonテスト**:
- **pytest**: メインテストフレームワーク
- **pytest-cov**: カバレッジ測定
- **pytest-mock**: モック機能
- **pytest-asyncio**: 非同期テスト対応
- **factory_boy**: テストデータ生成
- **Faker**: ダミーデータ生成

**データベーステスト**:
- **pytest-postgresql**: PostgreSQLテスト環境
- **SQLAlchemy**: ORM操作のテスト

**E2Eテスト**:
- **Playwright** または **Selenium**: ブラウザ自動化
- **pytest-playwright**: Playwright統合

**APIテスト**:
- **httpx**: 非同期HTTPクライアント
- **FastAPI TestClient**: FastAPI専用テストクライアント

## 6. テストファイル命名規約

### 6.1 ファイル名の規則
テストファイルは必ず `test_` プレフィックスで始めます。

**基本形式**:
```
test_<対象モジュール名>.py
```

### 6.2 ディレクトリ構造
テストファイルは、対象コードのディレクトリ構造を反映します。これは一例です。

```
tests/
├── unit/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── test_stock_service.py
│   │   └── test_portfolio_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── test_stock_repository.py
│   │   └── test_user_repository.py
│   └── utils/
│       ├── __init__.py
│       └── test_helpers.py
├── integration/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── test_stock_api.py
│   │   └── test_user_api.py
│   └── repositories/
│       ├── __init__.py
│       └── test_database_operations.py
└── e2e/
    ├── __init__.py
    ├── test_stock_analysis_flow.py
    └── test_portfolio_management_flow.py
```

### 6.3 テスト関数の命名規則
テスト関数は `test_` プレフィックスで始め、以下の形式を推奨します。

**形式1: 機能_条件_期待結果**
```python
def test_<機能>_<条件>_<期待結果>():
    pass

# 例
def test_create_stock_with_valid_data_returns_success():
    """正常な株式データで株式を作成すると成功を返す"""
    pass

def test_get_stock_price_when_not_found_raises_exception():
    """株価が見つからない場合は例外を発生させる"""
    pass
```

**形式2: 状況_期待動作**
```python
def test_<状況>_<期待動作>():
    pass

# 例
def test_invalid_stock_code_raises_validation_error():
    """無効な銘柄コードはバリデーションエラーを発生させる"""
    pass

def test_duplicate_stock_returns_conflict_error():
    """重複した株式は競合エラーを返す"""
    pass
```

### 6.4 テストクラスの命名規則
関連するテストをグループ化する場合は `Test` プレフィックスのクラスを使用します。

```python
class TestStockService:
    """StockServiceのテストグループ"""

    def test_create_stock_success(self):
        pass

    def test_create_stock_with_invalid_code_fails(self):
        pass


class TestStockServiceEdgeCases:
    """StockServiceのエッジケーステスト"""

    def test_create_stock_with_empty_name(self):
        pass

    def test_create_stock_with_extreme_price(self):
        pass
```

### 6.5 Fixtureファイルの命名
共通のフィクスチャは `conftest.py` に配置します。

```
tests/
├── conftest.py                    # 全テスト共通
├── unit/
│   ├── conftest.py                # 単体テスト共通
│   └── services/
│       └── conftest.py            # Servicesテスト共通
├── integration/
│   └── conftest.py                # 統合テスト共通
└── e2e/
    └── conftest.py                # E2Eテスト共通
```

### 6.6 テストデータファイルの命名
テスト用の静的データファイルは `fixtures/` ディレクトリに配置します。

```
tests/
└── fixtures/
    ├── sample_stock_data.json
    ├── test_portfolio.csv
    └── mock_api_responses/
        ├── stock_price_success.json
        └── stock_price_error.json
```

## 7. テストデータ管理

**原則**:
- テストごとに独立したデータを使用
- テスト間でデータを共有しない
- テスト終了後は必ずクリーンアップ

**方法**:
- **Fixture**: `conftest.py`で共通セットアップを定義
- **Factory**: `factory_boy`でモデルインスタンス生成
- **Transaction Rollback**: 統合テストではトランザクションロールバック
- **テストDB**: 本番DBとは完全に分離

**例**:
```python
@pytest.fixture
def test_db():
    """テスト用DB接続"""
    engine = create_engine(TEST_DATABASE_URL)
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)
```

## 8. モックとスタブの使用方針

**モック対象**:
- 外部API（株価データ取得など）
- メール送信
- ファイルシステムアクセス
- 時刻依存処理（`datetime.now()`など）
- 重い処理（長時間実行、リソース消費）

**モック不要**:
- 単純な計算ロジック
- データ変換処理
- バリデーション処理

**実装例**:
```python
def test_fetch_stock_price(mocker):
    """外部API呼び出しをモック"""
    mock_api = mocker.patch('app.services.stock_api.fetch_from_external')
    mock_api.return_value = {"price": 1500, "date": "2025-11-26"}

    result = stock_service.get_latest_price("1234")
    assert result.price == 1500
```

## 9. テストコード品質の維持

**レビュー観点**:
- テストが何を検証しているか明確か
- テストケース名が意図を表しているか
- 不要なモックを使っていないか
- テストが脆弱（flaky）でないか
- アサーションが適切か

**命名規則**:
```python
def test_<機能>_<条件>_<期待結果>():
    """
    例: test_create_stock_with_valid_data_returns_success
    """
    pass
```

**アンチパターン回避**:
- ❌ 複数の機能を1つのテストで検証
- ❌ テスト間で状態を共有
- ❌ 実装の詳細に依存したテスト
- ❌ 過度なモック使用
- ❌ テストのためだけのプロダクションコード

## 10. ベストプラクティス

1. **AAA パターンを遵守**
   - Arrange（準備）
   - Act（実行）
   - Assert（検証）

2. **1テスト1アサーション原則**
   - 可能な限り1つのテストで1つの事柄を検証

3. **明確なテストケース名**
   - 日本語コメントで意図を説明
   - テストケース名で何をテストしているか分かる

4. **独立性の確保**
   - テストの実行順序に依存しない
   - 並列実行可能

5. **高速化**
   - 不要なsleep/waitを避ける
   - 重い処理はモック化
   - 並列実行を活用

6. **継続的改善**
   - 失敗したテストは必ず修正
   - フレーキーテストは即座に対処
   - カバレッジレポートを定期的に確認

7. **ドキュメント化**
   - 複雑なテストはコメントで説明
   - セットアップ手順をREADMEに記載

---
