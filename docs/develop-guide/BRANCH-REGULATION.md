category: develop-guide
ai_context: low
last_updated: 2025-11-26
related_docs:
		- ../standards/git-workflow.md
		- ../develop-guide/README.md

# ブランチ規約

## 目次
- [ブランチ規約](#ブランチ規約)
  - [目次](#目次)
  - [1. 概要](#1-概要)
  - [2. ブランチ命名規則](#2-ブランチ命名規則)
  - [3. ブランチタイプ](#3-ブランチタイプ)
  - [4. ワークフロー](#4-ワークフロー)
  - [5. マージとレビュー](#5-マージとレビュー)
  - [6. リリースとタグ付け](#6-リリースとタグ付け)
  - [7. CI/CD とブランチ保護ルール](#7-cicd-とブランチ保護ルール)
  - [8. 例](#8-例)
  - [9. ベストプラクティス \& 注意点](#9-ベストプラクティス--注意点)

## 1. 概要
本ドキュメントは、リポジトリでのブランチ戦略と運用ルールを定めます。明確な命名規則、レビュー・マージ手順、および CI 連携を定義することで、共同開発の効率と品質を高めます。

## 2. ブランチ命名規則
ブランチは下記の命名規則に従って作成してください。小文字とハイフンを基本とし、スラッシュで分類を行います。

- `main` : 本番反映のための保護されたブランチ（プロダクション）
- `develop` : 開発統合用ブランチ（ステージング相当）
- `feature/<ISSUE番号>-short-description` : 新機能（例: `feature/123-add-search`）
- `fix/<ISSUE番号>-short-description` : バグ修正（例: `fix/210-fix-dup-insert`）
- `hotfix/<version>-short-description` : 本番緊急修正（例: `hotfix/1.2.1-fix-crash`）
- `release/<version>` : リリース準備用ブランチ（例: `release/1.2.0`）
- `chore/<topic>` : ビルドや CI 設定など雑務（例: `chore/update-deps`）
- `docs/<topic>` : ドキュメント変更（例: `docs/update-readme`）
- `experiment/<name>` : 実験的な作業（長期間放置しない）

命名ポイント:
- ISSUE番号がある場合は付ける（追跡しやすくするため）。
- `short-description` は英語または半角英数字で簡潔に。スペースは禁止。

## 3. ブランチタイプ
- **main**: 本番領域。直接 push 禁止。Pull Request（以下 PR）でのみ更新。
- **develop**: 日常的な統合先。feature ブランチは基本ここに向けて PR を出す。
- **feature**: 個別機能の実装。作業が完了したら develop に PR。
- **release**: リリース前の最終調整。バージョン番号で管理。ここでの修正は主にバージョン・ドキュメント・リリースノート等。
- **hotfix**: 緊急対応。main から分岐し、修正後は main と develop の双方にマージ。

## 4. ワークフロー
基本的な流れは Git Flow に準拠しますが、チームの規模やリリース頻度に合わせて柔軟に運用してください。

1. `feature` 開発
	 - `develop` から `feature/...` を作成。
	 - 小さな単位でコミット・PR を行う（1 PR = 1 目的）。
	 - ローカルはこまめに `develop` を取り込み、コンフリクトを早めに解消。
2. PR とレビュー
	 - PR は `develop` に向けて作成。
	 - 少なくとも1名のコードレビューを必須とする。
	 - CI が全て成功することをマージ条件とする。
3. リリース準備
	 - リリース作業は `release/<version>` ブランチで行う。
	 - 完了後、`release` を `main`（タグ付け）と `develop` にマージ。
4. ホットフィックス
	 - 本番で問題が見つかったら `main` から `hotfix/...` を作成し修正。
	 - 修正完了後、`hotfix` を `main` にマージしてタグ付け、その後 `develop` にもマージする。

## 5. マージとレビュー
- PR タイトルと本文は `commit-regulation.md` のフォーマットを意識して記載すること。
- マージ前に以下を満たすこと:
	- CI (テスト、リンター、型チェック等) が成功
	- 少なくとも1人の承認レビュー
	- WIP ラベルや Draft PR でないこと
- マージ戦略:
	- **Feature / Fix**: 基本は `Squash and merge` を推奨（履歴の見通しを良くするため）。
	- **Release / Hotfix**: 通常のマージ（履歴を残す）が許容される。
	- リポジトリ設定で自動マージ・Fast-forward を制限する場合はチームで合意すること。

## 6. リリースとタグ付け
- タグ形式: `vMAJOR.MINOR.PATCH`（例: `v1.2.0`）。
- タグは Annotated Tag を使うこと（説明と作者情報を保持）。
- リリース手順:
	- `release/<version>` を `main` にマージ。
	- `main` 上でタグを作成し、CI/CD が本番デプロイを開始する。
	- `release/<version>` の変更を `develop` にマージして同期する。

## 7. CI/CD とブランチ保護ルール
- ブランチ保護の推奨設定:
	- `main` と `develop` に対しては `force push` を禁止
	- プルリクエスト承認を必須（最低1名）
	- 必須ステータスチェック（例: テスト、Lint、Type Check）をオンにする
- CI 連携:
	- PR 作成時に自動でユニットテスト・静的解析を実行
	- `develop` にマージでステージングデプロイ、`main` にマージで本番デプロイをトリガ

## 8. 例
ブランチ作成・PR の例:

```
# 新機能ブランチ作成
git checkout -b feature/123-add-search develop

# 修正ブランチ作成
git checkout -b fix/210-fix-dup-insert develop

# ホットフィックス
git checkout -b hotfix/1.2.1-fix-crash main
```

## 9. ベストプラクティス & 注意点
- 1 コミットは原子性を保ち、1 PR は 1 目的で作る。
- 長期間放置するブランチは作らない（定期的に整理する）。
- `develop` と `main` の差分を最小に保つため、リリース済み修正は速やかに `develop` に同期する。
- ブランチ命名・PR 記述は自動的に CI やリリースに紐づく場合があるため一貫性を守る。
- 実験的な作業は `experiment/` で隔離し、長期化する場合はチームで方針を確認する。

---
