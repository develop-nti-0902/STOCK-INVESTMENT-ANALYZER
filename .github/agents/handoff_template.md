# Context

- 目的：
- 背景：
- 対象範囲：

# Task

- やること：
- やらないこと：

# Constraints

- 制約：
- 互換性：
- セキュリティ注意：

# Inputs

- 関連ファイル/ディレクトリ：
- 既存仕様：

# Expected Output

- 成果物：
- Done条件：

---
# ファイル配置と命名規約（運用ルール）

- Orchestrator はタスク開始時にメイン handoff を `.github/agents/handoffs/{task_id}.md` に作成します。
- サブエージェントは実行前にこのファイルを読み、実行後に自分の出力を `.github/agents/handoffs/{task_id}/{role}.md` に書き出します（例: `planner.md`, `coder.md`, `tester.md`）。
- Orchestrator が最終的な検証・集約を行う場合は `.github/agents/handoffs/{task_id}/aggregate.md` を作成します。
- `{task_id}` は日付やチケット番号、UUID 等、検出可能で一意な識別子を使ってください。

このテンプレートをコピーして handoff ファイルを作成してください。サブエージェントはこの形式を前提にパース/参照できます。

# Notes

- リスク：
- 確認事項：
