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

`.github/agents/00_orchestrator.md` の指示に従い、次の順で進める：

| # | エージェント | 用途 |
|---|---|---|
| 00 | Orchestrator | タスク全体を束ねる |
| 10 | Planner | 要件 → タスク分解 |
| 20 | Architect | API/DB 設計（必要時） |
| 30 | Coder | 最小差分実装 |
| 40 | Tester | テスト追加 |
| 50 | Reviewer | 4層品質ゲート |
| 60 | Security | 安全性点検（必要時） |

### HITL（必ず人間が承認する）

- データ削除・大量更新・破壊的マイグレーション
- 権限変更・認証/認可の方針変更
- 外部送信（メール/Slack/外部API）
- 本番設定変更・Secrets/鍵の取り扱い
