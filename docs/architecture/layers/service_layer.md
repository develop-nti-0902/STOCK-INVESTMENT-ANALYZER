---
category: architecture/layers
updated: 2026-03-06
related:
  - ../architecture_overview.md
  - ../architecture_diagram.md
---

# サービス層

## 役割

ドメインのビジネスロジックを実装し、複数のリポジトリ・外部 API を調整するオーケストレーション層です。スキーマで受け取った入力を内部表現に変換し、複数のリポジトリ操作を組み合わせ、結果をスキーマにマッピング可能な形式で返します。トランザクション管理、キャッシング戦略、バッチ処理フローもこの層の責務です。

## 依存方向

**上位（API 層）からの呼び出し**: スキーマに基づくデータ+引数
**下位（データアクセス層）への呼び出し**: リポジトリメソッド経由で永続化操作
**外部 API**: Yahoo Finance、EDINET、外部データソース

## 外部への依存

- リポジトリ層（データアクセスの抽象化）
- 外部 API（Yahoo Finance、EDINET）
- ユーティリティ・ヘルパー関数
- ログ・例外クラス

## 設計原則

- **ビジネスロジックの集約**: API レイヤーとデータアクセスレイヤーの調整役として、複雑なドメイン判断はここに集中
- **リポジトリ抽象化の活用**: 直接 DB にアクセスせず、常にリポジトリ経由で操作
- **非同期・並列処理**: 外部 API や大量データ処理は async/await で効率化
- **トランザクション管理**: 複数リポジトリ操作の一貫性をこの層で保証

## 他のレイヤーとの関係

**サービス層は、ビジネスロジックのすべてを集約**し、上下層のオーケストレーション役として機能します：

- **サービス層 ← API層**: 検証済み Pydantic スキーマをメソッド引数として受け取る
- **サービス層 → Repositories層**: 複数リポジトリの CRUD を組み合わせてビジネスプロセスを実現；**直接 SQL を書かない**
- **サービス層 ← Repositories層**: 取得した結果（ORM オブジェクト or スカラー値）を受け取る
- **サービス層 → 外部API**: Yahoo Finance、EDINET 等への API 呼び出しはここで集中管理；エラーハンドリング・リトライ戦略も担当
- **サービス層 ← → ドメイン判定・変換**: スキーマ → ドメインオブジェクト → ORM モデルへの変換処理
- **サービス層 → API層**: ドメインオブジェクト/リストを返す（API層がスキーマ整形を担当）

```mermaid
graph TB
  API["API層"]
  Service["サービス層"]
  Repo["Repositories層"]
  External["外部API (Yahoo Finance等)"]

  API -->|スキーマデータ| Service
  Service -->|複数リポジトリ組み合わせ| Repo
  Repo -->|取得結果| Service
  Service -->|トランザクション管理| Service
  Service -->|非同期並列呼び出し| External
  External -->|データ取得| Service
  Service -->|ドメインオブジェクト| API

  style Service fill:#e9ffec,stroke:#27a745,color:#000
  style API fill:#fff7e6,stroke:#e09b00,color:#000
  style Repo fill:#fff0f7,stroke:#c13b8b,color:#000
  style External fill:#fffce6,stroke:#d1b300,color:#000
```
