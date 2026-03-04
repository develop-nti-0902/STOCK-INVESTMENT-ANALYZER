# STOCK_MASTER テーブル正規化設計

## 概要
STOCK_MASTER テーブルを 3NF（第3正規形）に正規化し、データの一貫性と管理効率を向上させました。

## 背景
従来の STOCK_MASTER テーブルでは、以下のような冗長情報が保持されていました：

| カラム            | 型           | 説明                    |
| ----------------- | ------------ | ----------------------- |
| `sector_code_33`  | VARCHAR(10)  | 業種コード（33分類）    |
| `sector_name_33`  | VARCHAR(100) | 業種名（33分類） ← 重複 |
| `sector_code_17`  | VARCHAR(10)  | 業種コード（17分類）    |
| `sector_name_17`  | VARCHAR(100) | 業種名（17分類） ← 重複 |
| `market_category` | VARCHAR(50)  | 市場区分テキスト ← 重複 |
| `scale_code`      | VARCHAR(10)  | 規模コード              |
| `scale_category`  | VARCHAR(100) | 規模区分名 ← 重複       |

**問題点:**
- 業種名や規模名が複数カラムに重複保持
- データ変更時に全レコードを更新する必要性
- JOIN不要で直接値参照するため、不透明なメンテナンス

## 解決策：マスターテーブル化

### 新しいテーブル構成

#### 1. `market_category_master` テーブル
市場区分（プライム/スタンダード/グロース等）を一元管理

| カラム       | 型             | 説明                                                  |
| ------------ | -------------- | ----------------------------------------------------- |
| `id`         | INTEGER PK     | マスターテーブルID                                    |
| `code`       | VARCHAR(50) UK | マーケットカテゴリーコード（Prime/Standard/Growth等） |
| `name`       | VARCHAR(100)   | マーケットカテゴリー名                                |
| `created_at` | DATETIME       | 作成日時                                              |
| `updated_at` | DATETIME       | 更新日時                                              |

#### 2. `sector_33_master` テーブル
33業種分類を一元管理

| カラム       | 型             | 説明                     |
| ------------ | -------------- | ------------------------ |
| `id`         | INTEGER PK     | マスターテーブルID       |
| `code`       | VARCHAR(10) UK | 業種コード（08等）       |
| `name`       | VARCHAR(100)   | 業種名（水産・農林業等） |
| `created_at` | DATETIME       | 作成日時                 |
| `updated_at` | DATETIME       | 更新日時                 |

#### 3. `sector_17_master` テーブル
17業種分類を一元管理

| カラム       | 型             | 説明                       |
| ------------ | -------------- | -------------------------- |
| `id`         | INTEGER PK     | マスターテーブルID         |
| `code`       | VARCHAR(10) UK | 業種コード（1等）          |
| `name`       | VARCHAR(100)   | 業種名（水産物・農産物等） |
| `created_at` | DATETIME       | 作成日時                   |
| `updated_at` | DATETIME       | 更新日時                   |

#### 4. `scale_master` テーブル
企業規模分類を一元管理

| カラム       | 型             | 説明                  |
| ------------ | -------------- | --------------------- |
| `id`         | INTEGER PK     | マスターテーブルID    |
| `code`       | VARCHAR(10) UK | 規模コード（L/M/S等） |
| `name`       | VARCHAR(100)   | 規模名                |
| `created_at` | DATETIME       | 作成日時              |
| `updated_at` | DATETIME       | 更新日時              |

### 修正後の STOCK_MASTER テーブル

#### 削除されたカラム
- `sector_name_33` → sector_33_master へ
- `sector_name_17` → sector_17_master へ
- `scale_category` → scale_master へ

#### 追加された FK カラム
| カラム               | 型         | 説明                            |
| -------------------- | ---------- | ------------------------------- |
| `market_category_id` | INTEGER FK | market_category_master への参照 |
| `sector_33_id`       | INTEGER FK | sector_33_master への参照       |
| `sector_17_id`       | INTEGER FK | sector_17_master への参照       |
| `scale_id`           | INTEGER FK | scale_master への参照           |

#### 保持されるコードカラム
- `sector_code_33` ← 元データとの整合性確認用に保持
- `sector_code_17` ← 元データとの整合性確認用に保持
- `scale_code` ← 元データとの整合性確認用に保持

## データマイグレーション戦略

### 実行フロー
```
JPX データダウンロード
    ↓
fetch_and_extract_masters()
    ├─ 株データリスト抽出
    ├─ 一意な市場カテゴリー抽出
    ├─ 一意な33業種コード抽出
    ├─ 一意な17業種コード抽出
    └─ 一意な規模コード抽出
    ↓
save_with_masters()
    ├─ マスターテーブル作成（get_or_create パターン）
    │  ├─ market_category_master に INSERT/UPDATE
    │  ├─ sector_33_master に INSERT/UPDATE
    │  ├─ sector_17_master に INSERT/UPDATE
    │  └─ scale_master に INSERT/UPDATE
    ├─ FK ID の解決（stock_code → market_category_id, sector_33_id等）
    └─ StockMaster レコード一括 UPSERT
```

### 特徴
1. **JPX ダウンロード時点での有効値を基準**
   - JPX から取得したデータが真のマスター
   - 既存マスターは DELETE → RECREATE

2. **Idempotent パターン**
   - `get_or_create()` で重複を自動判定
   - 再実行時も安全

3. **Optional FK（nullable）**
   - 孤立レコード対応（存在しないマーケットカテゴリーの場合）
   - 「なし」状態を許容

## サービス層での利用

### Fetcher (`StockMasterFetcher`)
```python
async def fetch_and_extract_masters(self) -> dict:
    """
    JPX データ取得 + マスター値抽出

    Returns:
        {
            "market_categories": {"Prime": "Prime", ...},
            "sector_33": {"08": "水産・農林業", ...},
            "sector_17": {"1": "水産物・農産物", ...},
            "scale": {"L": "Large", ...},
            "stocks": [raw stock data list]
        }
    """
```

### Saver (`StockMasterSaver`)
```python
async def save_with_masters(self, data_dict: dict) -> int:
    """
    マスターテーブル作成 → FK 解決 → Upsert

    Args:
        data_dict: fetch_and_extract_masters() の戻り値

    Returns:
        永続化されたレコード数
    """
```

### Service (`StockMasterService`)
```python
async def sync_stock_master(self, limit: Optional[int] = None) -> int:
    """
    エンドツーエンドの sync 処理

    Flow:
        1. fetch_and_extract_masters() でデータ + マスター値抽出
        2. save_with_masters() でマスターテーブル作成 + FK 変換
        3. StockMasterUpdates 履歴記録
    """
```

## Screening Service での FK アクセス

### 修正前（テキスト直接参照）
```python
sector_code = stock.sector_code_17  # テキスト直接
```

### 修正後（FK 経由アクセス）
```python
if stock.sector_17:
    sector_code = stock.sector_17.code  # FK を通じてマスターから取得
```

### Eager Loading（N+1 回避）
```python
# screening で大量な stocks を処理する場合、eager load を使用
from sqlalchemy.orm import joinedload

stmt = select(StockMaster).options(
    joinedload(StockMaster.sector_17),
    joinedload(StockMaster.sector_33),
    joinedload(StockMaster.market_category),
    joinedload(StockMaster.scale),
)
```

## テストとマイグレーション

### Alembic マイグレーション (`9e1f5a7c8d0a`)
```
upgrade():
  1. 4つのマスターテーブルを CREATE
  2. FK 列を STOCK_MASTER に ADD
  3. インデックスを作成
  4. 古い name 列を DROP

downgrade():
  逆操作で、古いデータベーススキーマに戻す
```

### テスト
- Unit Tests: Models/Repositories/Services の単体テスト
- Integration Tests: マスター生成 → FK 解決 → Upsert の統合テスト
- E2E Tests: JPX fetch 全体フロー

## メリット

1. **データ一貫性**: 業種情報が 1 箇所で管理される
2. **保守効率**: マスターテーブルの更新で全 Stock に反映
3. **Query 最適化**: ForeignKey + Index で結合クエリが高速
4. **スケーラビリティ**: マスターテーブルは小規模なため、参照が高速
5. **監査トレイル**: created_at/updated_at で変更履歴が追跡可能

## デメリット・注意点

1. **N+1 Query**: joinedload() を使わないと大量 Query が発生
   - Screening で eager loading 活用
2. **マイグレーション**: 従来のテキストベース参照から FK 参照への移行
   - screening_service 修正が必須
3. **互換性**: 古いコードが sector_code_17 を直接参照すると エラー
   - sector_17.code に修正が必要

---

## 関連ドキュメント

- [ER Diagram](./er.md)
- [Data Structure](./data_structure.md)
- [Development Workflow](../develop-guide/development-workflow.md)
