---
title: Local Multi-Agent Workflow (Agents-as-Tools)
version: 0.1
---

# 標準フロー

このワークフローは中央の Orchestrator（`00_orchestrator.md`）が制御し、各工程はサブエージェント（Agents-as-Tools）として Orchestrator によって呼び出されます。サブエージェントは Orchestrator の指示に従って並列または逐次に実行され、処理結果は Orchestrator に集約されて最終判断されます。

主要な役割（すべてサブエージェントとして実装）:

1. Planner — 要件の分解と実行プラン作成
2. Architect — API/DB/仕様の設計（必要時）
3. Coder — 実装（最小差分）
4. Tester — ユニット/統合/e2e テストの実行
5. Reviewer — 品質ゲート（自動＋手動指摘）
6. Security — セキュリティ評価と HITL 判定（重要変更時）

各サブエージェントは handoff ファイル（`handoff_template.md` ベース）を介して入力／出力をやり取りします。Orchestrator は handoff の作成・検証・集約を行い、サブエージェントは所定のパスに自分の出力を書き出してください（詳細は `00_orchestrator.md` と `handoff_template.md` を参照）。

# ルーティング規則

| 状況 | 対応 |
|------|------|
| 仕様が曖昧 | Plannerで確認質問 → 確定後に進む |
| 新規API/DB変更 | Architectを必ず挟む |
| 重要フロー変更 | Testerでe2e優先 |
| 外部連携/権限/機密 | Securityを必ず挟む |
| HITL条件 | 承認待ちで停止 |
