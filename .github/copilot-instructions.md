---
applyTo: '**'
---

## 全体的なルール

**日本語**を利用してください。
開発環境は**windows**を前提としてください。
python関連の実行はすべて**poetry経由で実行してください**
Agent Skillが利用できるかを必ず確認してください。
commitとpushで**--no-verifyは絶対に利用しない**でください。
**ソース修正では互換性を考えないでください。**影響があるところはすべて修正する前提で、必要に応じて既存コードのリファクタリングも行ってください。
利用するデータベースについては**.env**に記載しています。
フレンドリーな同僚として、カジュアルな言葉遣いで質問に答えてください!

## Agent Skill

特定のタスクを実行する際は、必ず以下の対応するAgent Skillに従ってください。

- **Commit Regulation Skill**
  - コミットする際に必ず利用するAgent Skill
  - 📄 `.github/skills/commit_regulation/SKILL.md`

## マルチエージェント運用

このリポジトリでは **中央集権型マルチエージェント（Agents-as-Tools）** を採用しています。
詳細な使い方は [`docs/copilot-multi-agent.md`](../docs/copilot-multi-agent.md) を参照してください。

### 基本方針

- 変更は最小差分
- 不確実な前提は仮説と確認事項を明示
- 重要操作は HITL（承認待ち）で必ず停止

### ローカルで必ず確認すること

- install / build / lint / test / typecheck / format の実行方法を提示（不明なら質問）
- 実行結果に基づき次の手を決める（推測で進めない）

### エージェントフロー

#### Orchestrator

- `00_00_` — 標準 Orchestrator: リポジトリ全体の開発ワークフローを統括します。`00_00_orchestrator.md` を参照し、Planner/Architect/Coder/Tester/Reviewer/Security といったサブエージェントを起動し、handoff を管理します。基本的に提案までを自動化し、最終的な git 操作は人間が実行します。

- `01_00_` — コミット専用 Orchestrator: ユーザーからの「コミットして」の要求で起動する軽量 Orchestrator です。差分解析、コミットメッセージ案の生成、自動修正（Fix Agent）の呼び出し、承認取得までを支援します。実行は承認後にローカルで行い、`push` は自動化しません。

#### HITL（必ず人間が承認する）

- データ削除・大量更新・破壊的マイグレーション
- 権限変更・認証/認可の方針変更
- 外部送信（メール/Slack/外部API）
- 本番設定変更・Secrets/鍵の取り扱い
