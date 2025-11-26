# タスク管理ドキュメント

## 目次
- [タスク管理ドキュメント](#タスク管理ドキュメント)
  - [目次](#目次)
  - [概要](#概要)
  - [ファイル構成](#ファイル構成)
    - [主要ファイル](#主要ファイル)
    - [フォーマット定義 (`format/`)](#フォーマット定義-format)
  - [補足 / 運用](#補足--運用)

## 概要

- **目的**
	- このフォルダはプロジェクトのタスク管理に関する規約と実際のタスク情報を集約します。IssueやMilestoneの作成規約、フォーマット定義、実際のタスク一覧などを確認するためのドキュメント群です。

- **利用方法**
	- Issue作成時、Milestone設定時に参照してください。まず `format/` 配下の規約ドキュメントで作成ルールを確認し、テンプレートに従って作成してください。

## ファイル構成

### 主要ファイル
- [README.md](README.md) — この案内ファイル。
- [issue.md](issue.md) — 実際のIssue一覧や追跡情報（プロジェクト固有のタスク記録）。
- [milestones.md](milestones.md) — 実際のMilestone一覧や進捗状況（プロジェクト固有のマイルストーン記録）。

### フォーマット定義 (`format/`)
以下はIssueとMilestoneの作成規約とフォーマット定義です。各ファイルは作成時のルール、テンプレート、命名規則を説明します。
- [format/ISSUE-REGULATION.md](format/ISSUE-REGULATION.md) — Issue作成規約（タイトルフォーマット、本文テンプレート、Type定義）。
- [format/MILESTONES-REGULATION.md](format/MILESTONES-REGULATION.md) — Milestone作成規約（バージョニング、説明文テンプレート、命名規則）。

## 補足 / 運用

- ドキュメントは随時更新してください。規約変更がある場合は変更箇所と理由を追記してください。
- 新規Issue作成時は必ず `format/ISSUE-REGULATION.md` の規約に従ってください。
- Milestone設定時は `format/MILESTONES-REGULATION.md` のバージョニングルールを遵守してください。
- GitHubのIssueテンプレート（`.github/ISSUE_TEMPLATE/`）も併せて活用してください。
- より詳細な開発ワークフローについては `docs/develop-guide/` を参照してください。

---
