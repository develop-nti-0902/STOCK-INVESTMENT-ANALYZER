---
category: develop-guide
ai_context: high
last_updated: 2025-11-26
related_docs:
  - ../standards/git-workflow.md
  - ./COMMIT-REGULATION.md
  - ./BRANCH-REGULATION.md
---

# 開発ワークフロー

## 目次
- [開発ワークフロー](#開発ワークフロー)
  - [目次](#目次)
  - [1. 概要](#1-概要)
  - [2. 開発サイクル](#2-開発サイクル)
    - [2.1 スプリント期間](#21-スプリント期間)
    - [2.2 スプリントの流れ](#22-スプリントの流れ)
  - [3. Issue駆動開発](#3-issue駆動開発)
    - [3.1 Issueの作成](#31-issueの作成)
    - [3.2 Issueのラベル](#32-issueのラベル)
    - [3.3 Issueのステータス管理](#33-issueのステータス管理)
  - [4. 開発フロー](#4-開発フロー)
    - [4.1 基本的な作業フロー](#41-基本的な作業フロー)
    - [4.2 ブランチ運用](#42-ブランチ運用)
    - [4.3 コミット](#43-コミット)
    - [4.4 プルリクエスト](#44-プルリクエスト)
  - [5. レビュープロセス](#5-レビュープロセス)
    - [5.1 レビュー観点](#51-レビュー観点)
    - [5.2 レビュー対応](#52-レビュー対応)
  - [6. マージとデプロイ](#6-マージとデプロイ)
    - [6.1 マージ条件](#61-マージ条件)
    - [6.2 マージ後の対応](#62-マージ後の対応)
  - [7. ベストプラクティス](#7-ベストプラクティス)

## 1. 概要
本ドキュメントは、プロジェクトにおける開発ワークフローを定めます。Issue駆動のチケット制開発と定期的な開発サイクルを採用し、計画的かつ効率的な開発を実現することを目的とします。

**基本方針:**
- 全ての作業はIssueをベースに進める（チケット駆動開発）
- 定期的な開発サイクル（スプリント）で成果物を継続的に提供
- 小さく頻繁なリリースによる早期フィードバック
- ドキュメント・テスト・コードレビューの徹底

## 2. 開発サイクル

### 2.1 スプリント期間
- **スプリント期間**: 1週間
- **開始日**: 月曜日
- **終了日**: 日曜日

### 2.2 スプリントの流れ

| フェーズ               | タイミング             | 内容                                                                                                              |
| ---------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **計画**               | スプリント初日（月曜） | - 前スプリントの振り返り<br>- 次スプリントのゴール設定<br>- Issueの優先順位付けとアサイン<br>- 作業見積もりと計画 |
| **開発**               | Day 1-5                | - Issue単位での実装<br>- 日次での進捗確認<br>- 必要に応じてIssueの調整                                            |
| **テスト・レビュー**   | Day 6-7                | - コードレビュー<br>- 統合テスト<br>- ドキュメント整備<br>- 不具合修正                                            |
| **デプロイ・振り返り** | 最終日（日曜）         | - developブランチへのマージ<br>- デプロイ（必要に応じて）<br>- 成果の確認<br>- 振り返り（次回へ）                 |

## 3. Issue駆動開発

### 3.1 Issueの作成
全ての作業は必ずIssueを起点とします。

**Issueテンプレートの使用:**
GitHubでIssueを作成する際、作業の種類に応じて適切なテンプレートを選択してください。
以下のテンプレートが `.github/ISSUE_TEMPLATE/` に用意されています。

| テンプレート     | 用途                            | ファイル      |
| ---------------- | ------------------------------- | ------------- |
| 機能追加         | 新機能の追加や機能改善          | `feature.md`  |
| バグ報告         | バグや不具合の報告              | `bug.md`      |
| リファクタリング | コードの改善や内部構造の変更    | `refactor.md` |
| ドキュメント更新 | ドキュメントの追加・更新        | `docs.md`     |
| テスト追加・改善 | テストの追加や既存テストの改善  | `test.md`     |
| 雑務・環境整備   | ビルド、CI/CD、依存関係更新など | `chore.md`    |

各テンプレートには必要な項目が用意されているため、それに従って記入することで漏れなく情報を記載できます。

### 3.2 Issueのラベル

| ラベル                | 用途             |
| --------------------- | ---------------- |
| `type: feature`       | 新機能追加       |
| `type: bug`           | バグ修正         |
| `type: refactor`      | リファクタリング |
| `type: docs`          | ドキュメント更新 |
| `type: test`          | テスト追加・修正 |
| `type: chore`         | 雑務・環境整備   |
| `priority: high`      | 優先度: 高       |
| `priority: medium`    | 優先度: 中       |
| `priority: low`       | 優先度: 低       |
| `status: todo`        | 未着手           |
| `status: in-progress` | 作業中           |
| `status: review`      | レビュー待ち     |
| `status: done`        | 完了             |

### 3.3 Issueのステータス管理
1. **作成時**: `status: todo` ラベルを付与
2. **着手時**: `status: in-progress` に変更、自分にアサイン
3. **PR作成時**: `status: review` に変更
4. **マージ後**: Issueをクローズ、`status: done` を付与

## 4. 開発フロー

### 4.1 基本的な作業フロー

```
1. Issue作成/アサイン
   ↓
2. ブランチ作成
   ↓
3. 実装・テスト作成
   ↓
4. コミット（規約に従う）
   ↓
5. プッシュ
   ↓
6. プルリクエスト作成
   ↓
7. コードレビュー
   ↓
8. 修正対応（必要に応じて）
   ↓
9. マージ
   ↓
10. Issueクローズ
```

### 4.2 ブランチ運用
詳細は `BRANCH-REGULATION.md` を参照。

### 4.3 コミット
詳細は `COMMIT-REGULATION.md` を参照。

### 4.4 プルリクエスト

`.github/pull_request_template.md` にテンプレートが用意されています。

**PR作成時のチェックリスト:**
- [ ] タイトルがコミット規約に準拠
- [ ] Issue番号が記載されている（`Closes #XXX`）
- [ ] テンプレートの全項目が記入されている
- [ ] テストが追加されている
- [ ] ドキュメントが更新されている
- [ ] 全てのテストがパス
- [ ] Linter/Formatterが適用されている
- [ ] レビュアーがアサインされている

## 5. レビュープロセス

### 5.1 レビュー観点
1. **機能性**: 要件を満たしているか
2. **コード品質**: 可読性、保守性、拡張性
3. **テスト**: 適切なテストが書かれているか
4. **セキュリティ**: 脆弱性がないか
5. **パフォーマンス**: ボトルネックがないか
6. **ドキュメント**: 必要な説明が記載されているか
7. **標準準拠**: コーディング規約に従っているか

### 5.2 レビュー対応
- 議論が必要な場合はコメントで丁寧に説明
- 修正後は再レビューを依頼

## 6. マージとデプロイ

### 6.1 マージ条件
以下の条件を全て満たした場合のみマージ可能:
- [ ] 必須レビュアーの承認を得ている
- [ ] 全てのテストがパス
- [ ] コンフリクトが解消されている
- [ ] Linter/Formatterのエラーがない
- [ ] レビューコメントが全て解決済み

### 6.2 マージ後の対応
1. リモートブランチを削除
2. ローカルブランチをクリーンアップ
3. 関連Issueをクローズ
4. developブランチを最新に更新

```powershell
# マージ後のクリーンアップ
git checkout develop
git pull origin develop
git branch -d feature/101-stock-api
git remote prune origin
```

## 7. ベストプラクティス

**DO（推奨）:**
- ✅ 小さく頻繁にコミット
- ✅ こまめにプッシュしてバックアップ
- ✅ 早めにPR（Draft PR活用）
- ✅ レビューコメントから学ぶ姿勢
- ✅ 不明点は早めに相談
- ✅ ドキュメントとコードを同時に更新
- ✅ テストファーストで開発

**DON'T（禁止事項）:**
- ❌ 長期間ブランチを放置
- ❌ 巨大なPRを作成
- ❌ テストなしでマージ
- ❌ レビューコメントを無視
- ❌ フォーマッターを適用せずコミット
- ❌ Issue番号なしでコミット
- ❌ developに直接プッシュ

---

## 8. Stock Master Synchronization Workflow

### 概要
`stock_master` テーブルを JPX（日本取引所）からダウンロードしたデータで定期的に同期します。
正規化されたマスターテーブル（market_category/sector_33/sector_17/scale）と FK 参照を活用します。

### 実行シーケンス

```
1. Trigger (定期実行 or 手動)
        ↓
2. StockMasterService.sync_stock_master()
        ├─ 既存シンボルリストを取得
        ├─ StockMasterUpdates ログ作成（status: running）
        │
        ↓
3. Fetcher.fetch_and_extract_masters()
        ├─ JPX Excel ダウンロード
        ├─ 市場カテゴリー一覧抽出
        ├─ 業種(33分類) コード一覧抽出
        ├─ 業種(17分類) コード一覧抽出
        ├─ 規模カテゴリー一覧抽出
        └─ 戻り値: { "market_categories": {...}, "sector_33": {...}, ..., "stocks": [...] }
        │
        ↓
4. Saver.save_with_masters(data_dict)
        ├─ _create_masters() ← マスターテーブル分進行
        │  ├─ market_category_master.get_or_create(code, name)
        │  ├─ sector_33_master.get_or_create(code, name)
        │  ├─ sector_17_master.get_or_create(code, name)
        │  └─ scale_master.get_or_create(code, name)
        │
        ├─ _prepare_stock_data() ← FK ID 解決
        │  ├─ stock["sector_code_33"] → market_category_id 取得
        │  ├─ stock["sector_code_33"] → sector_33_id 取得
        │  ├─ stock["sector_code_17"] → sector_17_id 取得
        │  └─ stock["scale_code"] → scale_id 取得
        │
        └─ _upsert_stock_master_batch()
           ├─ DELETE FROM stock_master （既存データ削除）
           └─ INSERT ... （新規データ一括挿入）
        │
        ↓
5. StockCodeMapping.save_batch() ← JPX→EDINET マッピング同期
        │
        ↓
6. StockMasterUpdates.update_status(record_id, "success", {...})
        └─ added_stocks, updated_stocks, removed_stocks を記録
```

### 主な特徴

#### Idempotent パターン
- `get_or_create()` で既存マスターレコードの重複チェック
- 再実行時も安全（既存レコードは UPDATE されない）

#### Eager Loading
```python
# Screening Service での大量データ処理の場合
stmt = select(StockMaster).options(
    joinedload(StockMaster.market_category),
    joinedload(StockMaster.sector_33),
    joinedload(StockMaster.sector_17),
    joinedload(StockMaster.scale),
)
```

#### トランザクション管理
- `Saver.save_with_masters()` は明示的な rollback を持つ
- エラー発生時は全変更を Rollback

### デバッグ・トラブルシューティング

**Q: マスターテーブルが空のまま**
- A: `fetch_and_extract_masters()` が JPX データを正しく抽出しているか確認
  - 観点: JPX Excel ファイル形式が変更されていないか

**Q: 新しい業種コードが認識されない**
- A: `_extract_unique_sector_33()` で該当コードを抽出しているか確認
  - ロギング: `logger.debug()` で各マスター抽出結果を確認

**Q: Screening で "AttributeError: 'NoneType' object has no attribute 'code'"**
- A: FK が `None`（orphan stock）の可能性
  - 修正: `if stock.sector_17 is not None:` のチェック追加

---

**関連ドキュメント:**
- [Stock Master 正規化設計](../architecture/stock_master_normalization.md)
- [コミット規約](./COMMIT-REGULATION.md)
- [ブランチ規約](./BRANCH-REGULATION.md)
- [Git ワークフロー](../standards/git-workflow.md)
- [テスト標準](../standards/testing-standards.md)
