<!-- EDINET 一括ダウンロード & 抽出リファクタリング仕様 -->

# EDINET 一括ダウンロードおよびパーサ共用リファクタリング仕様

## 目的
- EDINET ドキュメントのダウンロード・解凍を一度だけ行い、同一の抽出成果物を使って複数のパーサ（例: `balance_sheet`, `profit_and_loss`）で順次データを抽出・保存する。
- 無駄なダウンロード・重複パースを排し、処理の原子性・可観測性を高める。

## 前提
- 現状、各サービスがそれぞれ `EdinetDocumentFetcher` 等を使って個別にダウンロード・解凍している。
- 各パーサは `Path` / `str` / `lxml.etree._Element` を受けられる（`profit_and_loss/parser.py` 等は既に対応済み）。

## 要件
1. ダウンロードはドキュメントごとに最大 1 回実行すること。
2. 同一ダウンロード成果（XBRL ファイル or parsed root）を複数パーサが再利用できること。
3. 関連テーブル（balance_sheet, profit_and_loss 等）は原子トランザクションで保存できることを原則とする（オプションで部分コミット許可）。
4. 成功／失敗いずれの場合も一時ファイルは削除されること（必ず cleanup を実行）。
5. 既存の公開 API を大きく壊さず段階的導入が可能であること。

## 提案コンポーネント（概要）
- `EdinetDownloadService`（新規）: ダウンロード + 解凍 + 抽出結果（Path, tmpdir, または parsed root）を返す。cleanup メソッドを提供。
- `EdinetAggregateUpdateService`（新規、オプション）: 単一ドキュメントを対象にダウンロード→複数パーサ実行→DB トランザクション保存→cleanup を統括。
- 既存 `EdinetDocumentFetcher`: そのまま利用可能だが、戻り値に作業ディレクトリ情報を含めるか `EdinetDownloadService` が作業ディレクトリを管理するよう変更を検討。
- `FileManager` の整理: 一時ファイル管理ロジックを共通化して責務を集中。

## API 仕様（主要メソッド）

- `EdinetDownloadService`:
  - `async download_and_extract(doc_id: str) -> Path` : 抽出された XBRL ファイルの Path を返す。
  - `async download_and_extract_root(doc_id: str) -> etree._Element` : （オプション）パース済みルートを返す。
  - `cleanup(path: Path) -> None` : 指定パス（抽出先）を削除する。

- `EdinetAggregateUpdateService`:
  - `async process_document(doc_id: str, parsers: list, transaction_atomic: bool = True) -> dict` : 指定ドキュメントを複数パーサで処理して保存。戻り値に保存数・ステータスを含む。

## 推奨フロー
1. `download_service.download_and_extract(doc_id)` を呼ぶ（1回のみ）。→ `xbrl_path`, `tmpdir` を取得
2. （推奨）`download_service` 側で一度 `lxml` パースして `root` を得る。各パーサに `parse_root(root)` を渡して解析（IO/パース重複の削減）
3. 各パーサの `converter` → `saver` を呼び出し、`EdinetAggregateUpdateService` 内で DB トランザクションを開始して一括保存
4. コミット成功後に `download_service.cleanup(tmpdir)` を実行
5. 例外発生時はロールバックして `cleanup` を実行。必要に応じて再試行ポリシーを適用

## パーサ側変更方針
- 互換性維持のため `parse(data: Any)` は残さない（削除）。
- 今後の保守性向上のため、`parse_root(root: etree._Element)` を公開 API として実装する。
- 必要に応じて、移行ヘルパーを短期的に用意して既存呼び出しをラップして移行を容易にする。
- 大量のファイルを扱う場合はメモリ負荷に注意し、`Path` 経由のパースも選べるようにする。

## トランザクション戦略
- デフォルト: 全関連テーブルの保存を一つのトランザクションでまとめてコミット（データ整合性優先）
- オプション: 設定で「個別保存モード（部分コミット可）」を有効化

-## エラーハンドリング
- ダウンロード失敗: リトライは行わない。ダウンロード失敗時は即座にエラーを返し、ログを記録して処理を中断する設計とする。
- パース失敗: 基本は全体ロールバックして処理終了。設定で該当パーサのみスキップするモードを許可
- cleanup は finally ブロックで必ず実行。cleanup の失敗は例外にしない（ログ記録のみ）

## テスト計画（要点）
- 単体: `EdinetDownloadService` のダウンロード、解凍、cleanup をモックで検証
- 単体: 各パーサの `parse_root` を fixture XBRL で検証
- 統合: `EdinetAggregateUpdateService` を用いた E2E（モック API or ZIP fixture）で保存・cleanup・トランザクションを検証

## 移行手順（段階的）
1. `EdinetDownloadService` を追加（既存 fetcher を内部で利用）
2. `profit_and_loss` のサービスをオプションで `download_service` を使うように切替、テスト
3. `balance_sheet` を同様に切替、テスト
4. 動作確認後、既存の個別ダウンロード呼び出しを削除

## 現行ファイル一覧（リファクタ前）
以下はリポジトリ内の現行ファイル（2026-02-11 時点）で、移行対象となる箇所です。

```
app/services/market_data/edinet/
├─ balance_sheet/
│  ├─ __init__.py
│  ├─ converter.py
│  ├─ fetcher.py
│  ├─ file_manager.py
│  ├─ parser.py
│  ├─ saver.py
│  └─ service.py
├─ profit_and_loss/
│  ├─ __init__.py
│  ├─ converter.py
│  ├─ fetcher.py      # 現状 balance_sheet の fetcher を再利用している（再エクスポート）
│  ├─ file_manager.py
│  ├─ parser.py
│  ├─ saver.py
│  └─ service.py
└─ common/
  ├─ api_client.py
  └─ xbrl_utils.py
```

## 提案ファイルツリー（詳細）
以下はリファクタ後にリポジトリ上で期待されるファイル/ディレクトリ構成の詳細案です。既存ファイルは可能な限りそのまま残しつつ、新規ファイルの追加と最小限の修正で段階的移行できるように設計しています。

```
app/services/market_data/edinet/
├─ download_service.py            # 新規: 統合ダウンロード API（既存 fetcher を内部利用）
├─ update_service.py              # 新規: オーケストレーション（Aggregate Update）
├─ file_manager.py                # 新規/共通化: 一時ファイル管理の共通実装
├─ balance_sheet/
│  ├─ __init__.py
│  ├─ converter.py                # 既存
│  ├─ fetcher.py                  # 既存（引き続き利用可。download_service 内で使う）
│  ├─ file_manager.py             # 既存（共通化後は削除）
│  ├─ parser.py                   # 既存 → `parse_root` を追加
│  ├─ saver.py                    # 既存
│  └─ service.py                  # 既存 → download_service をオプションで受け取るよう変更
├─ profit_and_loss/
│  ├─ __init__.py
│  ├─ converter.py                # 既存
│  ├─ fetcher.py                  # 既存（現状は balance_sheet.fetcher の再エクスポート）
│  ├─ file_manager.py             # 既存（共通化後は削除）
│  ├─ parser.py                   # 既存 → `parse_root` を追加
│  ├─ saver.py                    # 既存
│  └─ service.py                  # 既存 → download_service をオプションで受け取るよう変更
└─ common/
  ├─ api_client.py               # 既存
  └─ xbrl_utils.py               # 既存

tests/
├─ unit/
│  ├─ test_download_service.py    # 新規: download_service 単体テスト
│  ├─ test_parsers.py             # 既存/更新: parser の parse_root テスト
│  └─ ...
├─ integration/
│  └─ test_aggregate_update.py    # 新規: E2E に近い統合テスト
└─ e2e/
  └─ ...
```

---

## 削除予定ファイル（移行完了後に削除推奨）
移行が完了し、既存呼び出しをすべて `download_service` / 共通 `file_manager` に切り替えた後で削除を検討してください。
- `app/services/market_data/edinet/profit_and_loss/fetcher.py`  # 再エクスポートのみのため共通化後削除可
- `app/services/market_data/edinet/profit_and_loss/file_manager.py`  # balance_sheet と同一実装なら共通化後に削除
- `app/services/market_data/edinet/balance_sheet/file_manager.py`  # profit_and_loss と同一実装なら共通化後に削除
- `app/services/market_data/edinet/*/legacy_*`（将来発生しうるレガシーヘルパー）

> 注意: 削除は必ず機能テストと統合テスト後に行い、CI を通して影響範囲を確認してください。

## 変更対象ファイル（実装または修正が必要なファイル）
以下は移行時に必ず確認・修正すべきファイル群です。ファイル毎に想定される変更点も併記します。

- `app/services/market_data/edinet/download_service.py` (新規)
  - 役割: 既存の `EdinetDocumentFetcher` を内部で利用し、ダウンロード/解凍/parsed root の一元管理を提供
- `app/services/market_data/edinet/update_service.py` (新規推奨)
  - 役割: 複数パーサを呼び出しトランザクションで保存するオーケストレーション
- `app/services/market_data/edinet/file_manager.py` (新規/修正)
  - 役割: 一時ファイルの作成・探索・クリーンアップ機能の共通化
- `app/services/market_data/edinet/balance_sheet/service.py`
  - 変更: `download_service` をオプションで受け取るようにし、既存 fetcher 呼び出しを段階的に切替
- `app/services/market_data/edinet/profit_and_loss/service.py`
  - 変更: `download_service` をオプションで受け取るようにし、cleanup の責務を download_service 側へ委譲可能に
- `app/services/market_data/edinet/balance_sheet/parser.py`
  - 変更: `parse_root(root: etree._Element)` を追加して、外部でパース済 root を渡せるようにする
- `app/services/market_data/edinet/profit_and_loss/parser.py`
  - 変更: `parse_root(root: etree._Element)` を追加（`parse` は互換性維持）
- `app/services/market_data/edinet/*/fetcher.py`（各モジュールの fetcher）
  - 変更: fetch の戻り値仕様を `Path` or `(Path, tmpdir)` に揃える、または download_service に統合
- テスト関連: `tests/unit/*`, `tests/integration/*`, `tests/e2e/*`
  - 変更: 新サービスに対する単体テストと統合テストを追加

## 変更作業時のチェックリスト
- 変更前に必ずブランチを切る（例: `feature/edinet-download-unify`）
- 小さな段階で動作を確認する（`profit_and_loss` を先に切替）
- テストを充実させ、CI を通す
- 動作確認後に削除対象ファイルを削除し、再度 CI を実行


## スケジュール（短期）
1. 仕様確認・承認（本ドキュメント）：1日
2. `EdinetDownloadService` 実装 + 単体テスト：1–2日
3. `profit_and_loss` の切替 + 統合テスト：1日
4. `balance_sheet` 切替 + 統合テスト：1日
5. `EdinetAggregateUpdateService` 実装（原子コミット） + 統合/E2E：1–2日

---
このドキュメントに基づいて実装を続けますか？
