# EDINET 貸借対照表データベース 設計書

## 目次
- [EDINET 貸借対照表データベース 設計書](#edinet-貸借対照表データベース-設計書)
  - [目次](#目次)
  - [1. 概要](#1-概要)
    - [1.1 目的](#11-目的)
    - [1.2 データソース](#12-データソース)
    - [1.3 スコープ](#13-スコープ)
  - [2. データベース構造設計](#2-データベース構造設計)
    - [2.1 テーブル構成](#21-テーブル構成)
    - [2.2 一時ファイル管理（非データベース）](#22-一時ファイル管理非データベース)
    - [2.3 edinet\_balance\_sheets（EDINET貸借対照表データ）](#23-edinet_balance_sheetsedinet貸借対照表データ)
    - [2.3.1 XBRLタグとカラムの対応関係](#231-xbrlタグとカラムの対応関係)
    - [2.4 edinet\_profit\_and\_loss（EDINET損益・キャッシュフローデータ）](#24-edinet_profit_and_lossedinet損益キャッシュフローデータ)
    - [2.4.1 XBRLタグとカラムの対応関係](#241-xbrlタグとカラムの対応関係)
    - [2.5 進捗管理とエラーハンドリング](#25-進捗管理とエラーハンドリング)
  - [3. データ更新戦略](#3-データ更新戦略)
    - [3.1 最新データ優先ポリシー](#31-最新データ優先ポリシー)
    - [3.2 重複データの判定](#32-重複データの判定)
    - [3.3 データ更新フロー](#33-データ更新フロー)
  - [4. バッチ処理設計](#4-バッチ処理設計)
    - [4.1 処理フェーズ](#41-処理フェーズ)
    - [4.2 エラーハンドリング](#42-エラーハンドリング)
    - [4.3 並列処理](#43-並列処理)
  - [5. アーキテクチャレイヤー実装](#5-アーキテクチャレイヤー実装)
    - [5.1 モデル層（models/）](#51-モデル層models)
    - [5.2 スキーマ層（schemas/）](#52-スキーマ層schemas)
    - [5.3 リポジトリ層（repositories/）](#53-リポジトリ層repositories)
    - [5.4 サービス層（services/）](#54-サービス層services)
      - [5.4.1 共通処理（core/）](#541-共通処理core)
      - [5.4.2 EDINET共通処理（market\_data/edinet/common/）](#542-edinet共通処理market_dataedinetcommon)
      - [5.4.3 貸借対照表サービス（market\_data/edinet/balance\_sheet/）](#543-貸借対照表サービスmarket_dataedinetbalance_sheet)
      - [5.4.4 バッチ処理（batch/）](#544-バッチ処理batch)
  - [6. パフォーマンス最適化](#6-パフォーマンス最適化)
    - [6.1 インデックス設計](#61-インデックス設計)
    - [6.2 クエリ最適化](#62-クエリ最適化)
    - [6.3 バッチサイズ](#63-バッチサイズ)
  - [7. 運用・保守](#7-運用保守)
    - [7.1 マイグレーション手順](#71-マイグレーション手順)
    - [7.2 データメンテナンス](#72-データメンテナンス)
    - [7.3 監視項目](#73-監視項目)
  - [8. セキュリティ考慮事項](#8-セキュリティ考慮事項)
  - [9. 将来拡張性](#9-将来拡張性)

---

## 1. 概要

### 1.1 目的

EDINET（金融商品取引法に基づく有価証券報告書等の開示書類に関する電子開示システム）から取得した貸借対照表データを効率的に管理するためのデータベース設計。

**主要機能**:
- 有価証券報告書のメタデータ管理
- XBRL形式の貸借対照表データの解析・保存
- 最新データの優先適用（submission_date比較）
- 解析ステータスの追跡
- 同一年度データの自動更新（UPSERT）

### 1.2 データソース

| データソース  | 説明                                  | 形式       |
| ------------- | ------------------------------------- | ---------- |
| EDINET API    | 金融庁が提供する有価証券報告書取得API | JSON/ZIP   |
| XBRL ファイル | 財務諸表の構造化データ                | XML (XBRL) |

### 1.3 スコープ

**対象データ**:
- 有価証券報告書（年次）
- 貸借対照表の主要項目
  - 資産項目（総資産、流動資産、固定資産など）
  - 負債項目（総負債、流動負債、固定負債など）
  - 純資産項目（株主資本、利益剰余金など）
  - 財務指標（BPS、自己資本比率など）

**対象外**:
- 四半期報告書（将来拡張可能）
- 損益計算書、キャッシュフロー計算書（別システムで管理）
- 銀行向け特殊タグ（現段階では非対応）

**データ保存方針**:
- **ZIPファイル・XBRLファイル**: 一時ファイルとして保存し、解析完了後に削除（必要に応じて再ダウンロード可能）
- **処理管理情報**: `edinet_processing_status`テーブルで管理（doc_id, sec_code, xbrl_file_pathなど）
- **貸借対照表データ**: 永続化データとしてデータベースに保存

---

## 2. データベース構造設計

### 2.1 テーブル構成

```
edinet_balance_sheets          # 貸借対照表データ（永続化）
edinet_profit_and_loss         # 損益・キャッシュフローデータ（永続化）
```

**設計方針**:
- ダウンロードしたZIPファイル・XBRLファイルは**データベースに保存せず**、ローカルファイルシステムで一時管理
- 処理状態はメモリで管理し、全体の進捗は`batch_executions`テーブルで管理
- 貸借対照表の抽出に必要な情報（doc_id, submission_dateなど）は `edinet_balance_sheets` に直接保存
- 解析完了後、一時ファイル（ZIP、XBRL）を即座に削除
- UPSERT処理により、`(sec_code, period_end_date)`と`submission_date`で最新データのみ保持

### 2.2 一時ファイル管理（非データベース）

**目的**: ダウンロードしたZIPファイル・XBRLファイルの一時保存

**保存場所**: `data/edinet/{year}/{month}/{day}/`

**ファイル構成**:
```
data/edinet/
  └── 2019/                          # 年
      └── 11/                        # 月
          └── 06/                    # 日
              ├── S100H8H0.zip       # ダウンロードされたZIPファイル（EDINET APIから取得）
              └── S100H8H0/          # ZIPファイルを展開したディレクトリ（doc_idと同名）
                  ├── PublicDoc/     # 公衆縦覧書類
                  └── XBRL/          # XBRL形式の財務データ
                      ├── AuditDoc/  # 監査報告書
                      └── PublicDoc/ # XBRL本体
                          ├── *.xbrl # XBRLインスタンス文書
                          ├── *.xsd  # スキーマ定義
                          ├── *_cal.xml, *_def.xml, *_lab.xml, *_pre.xml # リンクベース
                          └── *.htm  # iXBRL形式の財務諸表
```

**ファイル処理フロー**:
1. **ZIPダウンロード**: EDINET APIから`{doc_id}.zip`をダウンロード（例: S100H8H0.zip）
2. **展開**: ZIPを解凍すると通常`{doc_id}/`ディレクトリが作成されるため、そのまま解凍する（既存ディレクトリがある場合は検出して適切に処理する）。
3. **XBRL解析**: `{doc_id}/XBRL/PublicDoc/*.xbrl`を解析
4. **データ保存**: `edinet_balance_sheets`テーブルにUPSERT
5. **削除**: 解析完了後、ZIPファイル・展開ディレクトリを即座に削除

**削除タイミング**:
- 貸借対照表データの抽出が成功した場合: 即座に削除（ZIPファイル、展開ディレクトリ）
- 解析エラーが発生した場合: エラーログに記録し、手動確認後に削除（デバッグ用に一時保持）

---

### 2.3 edinet_balance_sheets（EDINET貸借対照表データ）

**目的**: XBRLから解析した貸借対照表の財務データを保存

| カラム名                | 型             | NULL     | デフォルト        | 説明                                                      |
| ----------------------- | -------------- | -------- | ----------------- | --------------------------------------------------------- |
| id                      | SERIAL         | NOT NULL | -                 | 主キー（自動採番）                                        |
| doc_id                  | VARCHAR(50)    | NOT NULL | -                 | EDINET文書ID（例: S100N8ST）                              |
| sec_code                | VARCHAR(10)    | NOT NULL | -                 | 証券コード（例: 7203）                                    |
| filer_name              | VARCHAR(255)   | NULL     | -                 | 提出者名（企業名）                                        |
| submission_date         | DATE           | NOT NULL | -                 | 有価証券報告書の提出日                                    |
| period_end_date         | DATE           | NOT NULL | -                 | 決算期末日                                                |
| fiscal_year             | INTEGER        | NULL     | -                 | 会計年度（例: 2024）                                      |
| report_type             | VARCHAR(20)    | NOT NULL | 'annual'          | 報告種別（annual: 年次, quarterly: 四半期）               |
| total_assets            | NUMERIC(20, 2) | NULL     | -                 | 総資産（百万円）                                          |
| current_assets          | NUMERIC(20, 2) | NULL     | -                 | 流動資産（百万円）                                        |
| non_current_assets      | NUMERIC(20, 2) | NULL     | -                 | 固定資産（百万円）                                        |
| total_liabilities       | NUMERIC(20, 2) | NULL     | -                 | 総負債（百万円）                                          |
| current_liabilities     | NUMERIC(20, 2) | NULL     | -                 | 流動負債（百万円）                                        |
| non_current_liabilities | NUMERIC(20, 2) | NULL     | -                 | 固定負債（百万円）                                        |
| total_equity            | NUMERIC(20, 2) | NULL     | -                 | 純資産（百万円）                                          |
| shareholders_equity     | NUMERIC(20, 2) | NULL     | -                 | 株主資本（百万円）                                        |
| retained_earnings       | NUMERIC(20, 2) | NULL     | -                 | 利益剰余金（百万円）                                      |
| cash_and_equivalents    | NUMERIC(20, 2) | NULL     | -                 | 現金及び現金同等物（百万円）                              |
| short_term_loans        | NUMERIC(20, 2) | NULL     | -                 | 短期借入金（百万円、長期返済予定含む）                    |
| long_term_loans         | NUMERIC(20, 2) | NULL     | -                 | 長期借入金（百万円）                                      |
| bps                     | NUMERIC(10, 2) | NULL     | -                 | 1株当たり純資産（円）                                     |
| equity_to_asset_ratio   | NUMERIC(5, 2)  | NULL     | -                 | 自己資本比率（%）                                         |
| candidate_contexts      | VARCHAR(50)    | NULL     | -                 | 実際に解析で使用された `context`（例: FilingDateInstant） |
| candidate_keys          | VARCHAR(50)    | NULL     | -                 | 実際に解析で使用された `key`（例: jpcrp_cor:TotalAssets） |
| is_consolidated         | BOOLEAN        | NULL     | -                 | 連結決算フラグ（TRUE: 連結、FALSE: 単体）                 |
| created_at              | TIMESTAMP      | NOT NULL | CURRENT_TIMESTAMP | レコード作成日時                                          |
| updated_at              | TIMESTAMP      | NOT NULL | CURRENT_TIMESTAMP | レコード更新日時                                          |

### 2.3.1 XBRLタグとカラムの対応関係

**candidate_contexts（コンテキスト優先順位）**:
解析時には以下のコンテキストを優先順位順に検索します。
有価証券報告書には当期を含めて過去5年分のデータが含まれているため、各年度について順次解析を行います：

**当期（CurrentYear）**:
1. `CurrentYearInstant`: 当期末時点
2. `CurrentYearInstant_ConsolidatedMember`: 当期末時点（連結）
3. `CurrentYearInstant_NonConsolidatedMember`: 当期末時点（個別）

**前期（Prior1Year）**:
1. `Prior1YearInstant`: 前期末時点
2. `Prior1YearInstant_ConsolidatedMember`: 前期末時点（連結）
3. `Prior1YearInstant_NonConsolidatedMember`: 前期末時点（個別）

**前々期（Prior2Year）**:
1. `Prior2YearInstant`: 前々期末時点
2. `Prior2YearInstant_ConsolidatedMember`: 前々期末時点（連結）
3. `Prior2YearInstant_NonConsolidatedMember`: 前々期末時点（個別）

**3期前（Prior3Year）**:
1. `Prior3YearInstant`: 3期前末時点
2. `Prior3YearInstant_ConsolidatedMember`: 3期前末時点（連結）
3. `Prior3YearInstant_NonConsolidatedMember`: 3期前末時点（個別）

**4期前（Prior4Year）**:
1. `Prior4YearInstant`: 4期前末時点
2. `Prior4YearInstant_ConsolidatedMember`: 4期前末時点（連結）
3. `Prior4YearInstant_NonConsolidatedMember`: 4期前末時点（個別）

**candidate_keys（XBRLタグ）とカラムの対応**:

| カラム名                | XBRLタグ（candidate_keys）                                                            | 備考                                                            |
| ----------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| total_assets            | `jpcrp_cor:TotalAssetsSummaryOfBusinessResults`                                       | 総資産（経営指標サマリーから取得）                              |
| total_equity            | `jpcrp_cor:NetAssetsSummaryOfBusinessResults`<br>`jppfs_cor:NetAssets`                | 純資産（タグ名は"NetAssets"だが純資産を指す）<br>候補を順に探索 |
| shareholders_equity     | `jppfs_cor:ShareholdersEquity`<br>`jppfs_cor:NetAssets`                               | 株主資本<br>見つからない場合は純資産で代用                      |
| retained_earnings       | `jppfs_cor:RetainedEarnings`                                                          | 利益剰余金                                                      |
| short_term_loans        | `jppfs_cor:ShortTermLoansPayable`<br>`jppfs_cor:CurrentPortionOfLongTermLoansPayable` | 短期借入金 + 長期借入金の当期返済予定額<br>両方のタグの値を合算 |
| long_term_loans         | `jppfs_cor:LongTermLoansPayable`                                                      | 長期借入金                                                      |
| bps                     | `jpcrp_cor:NetAssetsPerShareSummaryOfBusinessResults`                                 | 1株当たり純資産（経営指標サマリーから取得）                     |
| equity_to_asset_ratio   | `jpcrp_cor:EquityToAssetRatioSummaryOfBusinessResults`                                | 自己資本比率（0-1の値は%に変換）                                |
| current_assets          | **未確認**                                                                            | 今後調査予定（候補: `jppfs_cor:CurrentAssets`）                 |
| non_current_assets      | **未確認**                                                                            | 今後調査予定（候補: `jppfs_cor:NonCurrentAssets`）              |
| total_liabilities       | **未確認**                                                                            | 今後調査予定（候補: `jppfs_cor:Liabilities`）                   |
| current_liabilities     | **未確認**                                                                            | 今後調査予定（候補: `jppfs_cor:CurrentLiabilities`）            |
| non_current_liabilities | **未確認**                                                                            | 今後調査予定（候補: `jppfs_cor:NonCurrentLiabilities`）         |
| cash_and_equivalents    | **未確認**                                                                            | 今後調査予定（候補: `jppfs_cor:CashAndCashEquivalents`）        |

**特記事項**:
- **銀行向けタグは現段階では非対応**: 銀行業の財務諸表では異なるタグ体系が使用されます（例: `jppfs_cor:BorrowedMoneyLiabilitiesBNK`など）。現状は一般事業会社向けのタグのみ対応しており、銀行向けタグは将来拡張として対応予定です。
- **複数タグの合算処理**: `short_term_loans`は`ShortTermLoansPayable`と`CurrentPortionOfLongTermLoansPayable`の合算値として算出します。
- **未確認タグの調査方針**: 上記表で「未確認」とマークされたカラムについては、実際のXBRLファイルを解析して適切なタグを特定する必要があります。調査後に本ドキュメントを更新します。
- **タグの名前空間**:
  - `jpcrp_cor`: 企業内容等の開示に関する内閣府令（Consolidated Results）
  - `jppfs_cor`: 財務諸表等の用語、様式及び作成方法に関する規則（Financial Statements）

**制約・インデックス**:
```sql
PRIMARY KEY (id)
INDEX idx_edinet_bs_doc_id (doc_id)
INDEX idx_edinet_bs_sec_code (sec_code)
INDEX idx_edinet_bs_period_end (period_end_date DESC)
INDEX idx_edinet_bs_sec_period (sec_code, period_end_date DESC)
UNIQUE (sec_code, period_end_date)
```

**特徴**:
- `doc_id` はEDINET文書IDで、重複提出を識別
- **UNIQUE制約**: `(sec_code, period_end_date)` で同一年度は1レコードのみ保持
- `submission_date` で最新データを判定し、新しい提出日のデータが来たら既存レコードを**UPDATE**
- 金額は百万円単位で保存（NUMERIC(20, 2)で十分な精度）
- `is_consolidated` で連結/単体を区別
- `short_term_loans` は短期借入金と長期借入金返済予定額の合算
- **外部キーなし**: メタデータテーブルが存在しないため、doc_idは参照整合性チェックなし

---

### 2.4 edinet_profit_and_loss（EDINET損益・キャッシュフローデータ）

**目的**: XBRLから解析した損益計算書およびキャッシュフロー計算書の財務データを保存

| カラム名           | 型             | NULL     | デフォルト        | 説明                                                                                            |
| ------------------ | -------------- | -------- | ----------------- | ----------------------------------------------------------------------------------------------- |
| id                 | SERIAL         | NOT NULL | -                 | 主キー（自動採番）                                                                              |
| doc_id             | VARCHAR(50)    | NOT NULL | -                 | EDINET文書ID（例: S100N8ST）                                                                    |
| sec_code           | VARCHAR(10)    | NOT NULL | -                 | 証券コード（例: 7203）                                                                          |
| submission_date    | DATE           | NOT NULL | -                 | 有価証券報告書の提出日                                                                          |
| period_end_date    | DATE           | NOT NULL | -                 | 決算期末日                                                                                      |
| fiscal_year        | INTEGER        | NULL     | -                 | 会計年度（例: 2024）                                                                            |
| report_type        | VARCHAR(20)    | NOT NULL | 'annual'          | 報告種別（annual: 年次, quarterly: 四半期）                                                     |
| operating_profit   | NUMERIC(20, 2) | NULL     | -                 | 営業キャッシュフロー（百万円）                                                                  |
| eps                | NUMERIC(20, 2) | NULL     | -                 | EPS（1株当たり当期純利益、円）                                                                  |
| candidate_contexts | VARCHAR(50)    | NULL     | -                 | 実際に解析で使用された `context`（例: CurrentYearDuration）                                     |
| candidate_keys     | VARCHAR(50)    | NULL     | -                 | 実際に解析で使用された `key`（例: jpcrp_cor:BasicEarningsLossPerShareSummaryOfBusinessResults） |
| is_consolidated    | BOOLEAN        | NULL     | -                 | 連結決算フラグ（TRUE: 連結、FALSE: 単体）                                                       |
| created_at         | TIMESTAMP      | NOT NULL | CURRENT_TIMESTAMP | レコード作成日時                                                                                |
| updated_at         | TIMESTAMP      | NOT NULL | CURRENT_TIMESTAMP | レコード更新日時                                                                                |

### 2.4.1 XBRLタグとカラムの対応関係

**candidate_contexts（コンテキスト優先順位）**:
解析時には以下のコンテキストを優先順位順に検索します。
有価証券報告書には当期を含めて過去5年分のデータが含まれているため、各年度について順次解析を行います：

**当期（CurrentYear）**:
1. `CurrentYearDuration`: 当期末時点
2. `CurrentYearDuration_ConsolidatedMember`: 当期末時点（連結）
3. `CurrentYearDuration_NonConsolidatedMember`: 当期末時点（個別）

**前期（Prior1Year）**:
1. `Prior1YearDuration`: 前期末時点
2. `Prior1YearDuration_ConsolidatedMember`: 前期末時点（連結）
3. `Prior1YearDuration_NonConsolidatedMember`: 前期末時点（個別）

**前々期（Prior2Year）**:
1. `Prior2YearDuration`: 前々期末時点
2. `Prior2YearDuration_ConsolidatedMember`: 前々期末時点（連結）
3. `Prior2YearDuration_NonConsolidatedMember`: 前々期末時点（個別）

**3期前（Prior3Year）**:
1. `Prior3YearDuration`: 3期前末時点
2. `Prior3YearDuration_ConsolidatedMember`: 3期前末時点（連結）
3. `Prior3YearDuration_NonConsolidatedMember`: 3期前末時点（個別）

**4期前（Prior4Year）**:
1. `Prior4YearDuration`: 4期前末時点
2. `Prior4YearDuration_ConsolidatedMember`: 4期前末時点（連結）
3. `Prior4YearDuration_NonConsolidatedMember`: 4期前末時点（個別）

**candidate_keys（XBRLタグ）とカラムの対応**:

| カラム名         | XBRLタグ（candidate_keys）                                    | 備考                                                             |
| ---------------- | ------------------------------------------------------------- | ---------------------------------------------------------------- |
| eps              | `jpcrp_cor:BasicEarningsLossPerShareSummaryOfBusinessResults` | 1株当たり当期純利益（経営指標サマリーから取得）                  |
| operating_profit | `jppfs_cor:NetCashProvidedByUsedInOperatingActivities`        | 営業活動によるキャッシュフロー（キャッシュフロー計算書から取得） |

**特記事項**:
- **コンテキストの違い**: 貸借対照表では `Instant`（時点）を使用しますが、損益計算書とキャッシュフロー計算書では `Duration`（期間）を使用します。
- **EPS（1株当たり当期純利益）**: 経営指標等のサマリーから取得します。企業によっては基本的EPSと希薄化後EPSの両方が記載されている場合がありますが、ここでは基本的EPSを使用します。
- **営業キャッシュフロー**: キャッシュフロー計算書の営業活動セクションから取得します。プラスの値は現金の増加、マイナスの値は現金の減少を示します。
- **タグの名前空間**:
  - `jpcrp_cor`: 企業内容等の開示に関する内閣府令（Consolidated Results）
  - `jppfs_cor`: 財務諸表等の用語、様式及び作成方法に関する規則（Financial Statements）

**制約・インデックス**:
```sql
PRIMARY KEY (id)
INDEX idx_edinet_pl_doc_id (doc_id)
INDEX idx_edinet_pl_sec_code (sec_code)
INDEX idx_edinet_pl_period_end (period_end_date DESC)
INDEX idx_edinet_pl_sec_period (sec_code, period_end_date DESC)
UNIQUE (sec_code, period_end_date)
```

**特徴**:
- `doc_id` はEDINET文書IDで、重複提出を識別
- **UNIQUE制約**: `(sec_code, period_end_date)` で同一年度は1レコードのみ保持
- `submission_date` で最新データを判定し、新しい提出日のデータが来たら既存レコードを**UPDATE**
- 金額は百万円単位で保存（EPSは円単位）
- `is_consolidated` で連結/単体を区別
- **外部キーなし**: メタデータテーブルが存在しないため、doc_idは参照整合性チェックなし

---

### 2.5 進捗管理とエラーハンドリング

**バッチ全体の進捗管理**: 既存の `batch_executions` テーブルを使用

- バッチタイプ: `edinet_balance_sheet_fetch`
- 全体の進捗（`total_stocks`, `processed_stocks`, `successful_stocks`, `failed_stocks`）
- ジョブのステータス（'running', 'completed', 'failed'）
- バッチ処理中に定期的に進捗を更新（例: 10件処理ごと）

**個別書類の処理**:
- バッチループ内で順次または並列処理（非同期処理）
- 各書類の処理は独立しており、状態管理テーブルは不要
- エラー発生時は構造化ログファイルに記録（`logs/edinet_processing/{date}.log`）
- 処理結果（成功/失敗）は`batch_executions`の集計カウンターに反映

**データ更新の方針**:
- **すべての書類をダウンロード・解析**（重複チェックなし）
- UPSERT処理（3.2節）で自動的に最新データのみ保存:
  - `(sec_code, period_end_date)`が同一の場合、`submission_date`を比較
  - 新しい`submission_date` → UPDATE（既存レコードを更新）
  - 古い`submission_date` → スキップ（WHERE句でUPDATEをブロック）
- **メリット**:
  - 訂正報告が提出された場合、自動的に最新データに更新
  - カラム追加や解析ロジック改善時、全データを再処理可能
  - シンプルで堅牢な設計

**エラーログ形式**:
```json
{
  "timestamp": "2026-01-29T10:30:00Z",
  "doc_id": "S100H8H0",
  "sec_code": "7203",
  "phase": "parsing",
  "error": "XBRL tag not found: jpcrp_cor:TotalAssets",
  "xbrl_file_path": "data/edinet/2019/11/06/S100H8H0/XBRL/PublicDoc/..."
}
```

---

## 3. データ更新戦略

### 3.1 最新データ優先ポリシー

**原則**: 同一銘柄・同一決算期に対して、最も提出日が新しい有価証券報告書のデータを正とする。

**理由**:
- 有価証券報告書は訂正報告が提出されることがある
- 後から提出されたデータが最も正確

**実装方針**:
- 同一年度のデータは**1レコードのみ保持**（履歴なし）
- `submission_date` を比較し、新しいデータで既存レコードを**UPDATE**
- 古い `submission_date` のデータは**無視**（INSERT/UPDATE しない）

### 3.2 重複データの判定

**判定キー**: `(sec_code, period_end_date)`

**UNIQUE制約**: `UNIQUE (sec_code, period_end_date)` により、同一年度は物理的に1レコードのみ存在

**データ更新ロジック**:
1. 既存データの存在確認: `SELECT * FROM edinet_balance_sheets WHERE sec_code = ? AND period_end_date = ?`
2. 既存データなし → **INSERT**
3. 既存データあり:
   - 新しい `submission_date` ≧ 既存の `submission_date` → **UPDATE**（全カラム更新）
   - 新しい `submission_date` < 既存の `submission_date` → **スキップ**（何もしない）

**判定SQL例**:
```sql
-- UPSERT処理（PostgreSQL）
INSERT INTO edinet_balance_sheets (
  doc_id, sec_code, submission_date, period_end_date, ...
) VALUES (
  :doc_id, :sec_code, :submission_date, :period_end_date, ...
)
ON CONFLICT (sec_code, period_end_date)
DO UPDATE SET
  doc_id = EXCLUDED.doc_id,
  submission_date = EXCLUDED.submission_date,
  total_assets = EXCLUDED.total_assets,
  -- ... 他のカラム
  updated_at = CURRENT_TIMESTAMP
WHERE EXCLUDED.submission_date >= edinet_balance_sheets.submission_date;
```

### 3.3 データ更新フロー

```
1. バッチ開始: batch_executionsにレコード作成（status='running'）
   ↓
2. EDINET APIから書類一覧を取得
   ↓
3. 各書類について:
   - ZIPダウンロード・解凍
   - XBRL解析実行（当期+過去4年分の計5年分を取得）:
     * CurrentYearInstant（当期）
     * Prior1YearInstant（前期）
     * Prior2YearInstant（前々期）
     * Prior3YearInstant（3期前）
     * Prior4YearInstant（4期前）
   - 各年度についてUPSERT処理を実行:
     * UNIQUE制約 (sec_code, period_end_date) で既存データを検索
     * 既存データなし → INSERT
     * 既存データあり:
       - 新しい submission_date → UPDATE（全カラム更新）
       - 古い submission_date → スキップ（WHERE句でブロック、DB更新なし）
   - 一時ファイル即座に削除
   - batch_executionsの進捗カウンターを更新
   ↓
4. バッチ完了: batch_executionsをstatus='completed'に更新
```

**重要**:
- UPSERT処理により、同一年度のデータは常に最新の `submission_date` のものが保持される
- 処理状態はメモリで管理し、データベースへの書き込みは最小限に

**トランザクション境界**:
- 1書類ごとにトランザクション管理
- 途中失敗時は該当書類のみロールバック（エラーログに記録）
- 他の書類の処理は継続

---

## 4. バッチ処理設計

### 4.1 処理フェーズ

**Phase 1: 初期化**

処理ステップ：
1. batch_executionsテーブルにレコード作成（batch_type='edinet_balance_sheet_fetch', status='running'）
2. 対象期間の検証（start_date, end_dateの妥当性チェック）

**Phase 2: 書類検索・処理**

処理ステップ：
1. 対象期間の日付範囲でループ処理
2. EDINET APIから有価証券報告書を検索（doc_type=2）
3. 各書類について以下を実施：
   - 一時ディレクトリ（`work/edinet_temp/{date}/{doc_id}/`）にZIPファイルを保存・解凍
   - XBRLファイルを解析し、貸借対照表データを抽出（当期+過去4年分の計5年分）
   - 各年度（CurrentYear, Prior1Year, Prior2Year, Prior3Year, Prior4Year）についてUPSERT処理を実行（submission_date比較で最新データのみ保存）
   - 一時ファイル（ZIPファイル、XBRL）を即座に削除
   - batch_executionsの進捗カウンターを更新（processed_stocks++）
4. エラー発生時:
   - エラーログファイルに記録（logs/edinet_processing/）
   - batch_executionsのfailed_stocksをインクリメント
   - 処理を継続

**Phase 3: 完了処理**

処理ステップ：
1. batch_executionsテーブルを更新（status='completed', end_time=現在時刻）
2. 処理結果をログに出力（成功数、失敗数、処理時間）

### 4.2 エラーハンドリング

**エラー分類**:
| エラー種別             | 処理                                                                            |
| ---------------------- | ------------------------------------------------------------------------------- |
| ネットワークエラー     | リトライ（最大3回）、失敗時はエラーログ記録                                     |
| XBRL解析エラー         | エラーログ記録、batch_executionsのfailed_stocksをインクリメント                 |
| データ不足（タグなし） | 警告ログ記録、batch_executionsのsuccessful_stocksをインクリメント（部分的成功） |
| DB接続エラー           | 処理中断、batch_executionsをstatus='failed'に更新、アラート送信                 |

**ログ記録**:
- すべてのエラーは構造化ログとしてファイルに出力（`logs/edinet_processing/{date}.log`）
- JSON形式で記録（後の分析が容易）
- 重大なエラー（DB接続エラーなど）はbatch_executionsのerror_messageカラムにも記録

### 4.3 並列処理

**推奨設定**:
- ダウンロード: 並列度 3-5（EDINET APIへの負荷考慮）
- XBRL解析: 並列度 5-10（CPUバウンド処理）

**実装方針**:
- 非同期処理（asyncio）を使用した並列ダウンロード
- セマフォによる同時実行数の制御
- エラー発生時も他のタスクは継続実行

---

## 5. アーキテクチャレイヤー実装

### 5.1 モデル層（models/）

**ファイル構成**:
```
app/models/
  └── edinet_balance_sheet.py      # EdinetBalanceSheet モデル
```

**Note**: 処理ステータスはメモリで管理するため、専用モデルは不要

**モデル設計方針**:
- SQLAlchemyのORMマッピングを使用
- BaseモデルからSerialPKMixin、TimestampMixinを継承
- テーブル名: `edinet_balance_sheets`
- カラム定義:
  - **EDINET書類情報**:
    - `doc_id`: 文書ID（String(50), NOT NULL, indexed）
    - `sec_code`: 証券コード（String(10), NOT NULL, indexed）
    - `filer_name`: 提出者名（String(255), NULL）
    - `submission_date`: 提出日（Date, NOT NULL）
    - `period_end_date`: 決算期末日（Date, NOT NULL, indexed）
    - `fiscal_year`: 会計年度（Integer, NULL）
    - `report_type`: 報告種別（String(20), NOT NULL, default="annual"）
  - **貸借対照表データ（資産）**:
    - `total_assets`: 総資産（Numeric(20, 2), NULL）
    - `current_assets`: 流動資産（Numeric(20, 2), NULL）
    - `non_current_assets`: 固定資産（Numeric(20, 2), NULL）
    - `cash_and_equivalents`: 現金及び現金同等物（Numeric(20, 2), NULL）
  - **貸借対照表データ（負債）**:
    - `total_liabilities`: 総負債（Numeric(20, 2), NULL）
    - `current_liabilities`: 流動負債（Numeric(20, 2), NULL）
    - `non_current_liabilities`: 固定負債（Numeric(20, 2), NULL）
    - `short_term_loans`: 短期借入金（Numeric(20, 2), NULL）
    - `long_term_loans`: 長期借入金（Numeric(20, 2), NULL）
  - **貸借対照表データ（純資産）**:
    - `total_equity`: 純資産（Numeric(20, 2), NULL）
    - `shareholders_equity`: 株主資本（Numeric(20, 2), NULL）
    - `retained_earnings`: 利益剰余金（Numeric(20, 2), NULL）
  - **財務指標**:
    - `bps`: 1株当たり純資産（Numeric(10, 2), NULL）
    - `equity_to_asset_ratio`: 自己資本比率（Numeric(5, 2), NULL）
  - **メタ情報**:
    - `candidate_contexts`: 実際に解析で使用された `context`（String(50), NULL）
    - `candidate_keys`: 実際に解析で使用された `key`（String(50), NULL）

    - `is_consolidated`: 連結決算フラグ（Boolean, NULL）
- インデックス定義:
  - 単一インデックス: `idx_edinet_bs_doc_id` (doc_id)
  - 単一インデックス: `idx_edinet_bs_sec_code` (sec_code)
  - 単一インデックス: `idx_edinet_bs_period_end` (period_end_date DESC)
  - 複合インデックス: `idx_edinet_bs_sec_period` (sec_code, period_end_date DESC)
  - UNIQUE制約: `uq_edinet_bs_sec_period` (sec_code, period_end_date) で同一年度は1レコードのみ

### 5.2 スキーマ層（schemas/）

**ファイル構成**:
```
app/schemas/
  └── edinet_balance_sheet.py      # EdinetBalanceSheetCreate, EdinetBalanceSheetRead
```

**スキーマ設計方針**:
- Pydanticモデルを使用したバリデーションとシリアライゼーション
- スキーマクラス:
  - `EdinetBalanceSheetBase`: 基底スキーマ（全フィールド定義）
    - doc_id, sec_code, filer_name, submission_date, period_end_date, fiscal_year, report_type
    - total_assets, current_assets, non_current_assets, cash_and_equivalents
    - total_liabilities, current_liabilities, non_current_liabilities, short_term_loans, long_term_loans
    - total_equity, shareholders_equity, retained_earnings
    - bps, equity_to_asset_ratio
    - candidate_contexts, candidate_keys, is_consolidated
  - `EdinetBalanceSheetCreate`: 作成用スキーマ（入力バリデーション）
    - EdinetBalanceSheetBaseを継承
    - 全フィールドの入力バリデーション実施
  - `EdinetBalanceSheetRead`: 読み取り用スキーマ（レスポンス用）
    - EdinetBalanceSheetBaseを継承
    - 追加フィールド: id, created_at, updated_at
    - model_config = ConfigDict(from_attributes=True)
  - `EdinetBalanceSheetLatest`: 最新データ検索用（軽量スキーマ）
    - 含むフィールド: sec_code, period_end_date, total_assets, total_equity, bps, equity_to_asset_ratio
    - APIレスポンスの最適化用
  - `ProcessingStatusCreate`: ステータス作成用スキーマ
    - 含むフィールド: doc_id, sec_code, status, xbrl_file_path
  - `ProcessingStatusUpdate`: ステータス更新用スキーマ
    - 含むフィールド: status, processing_started_at, processing_completed_at, error_message
- バリデーションルール:
  - 文字列長の制限: doc_id (max=50), sec_code (max=10), filer_name (max=255), report_type (max=20), candidate_contexts (max=50), candidate_keys (max=50)
  - 必須フィールド: doc_id, sec_code, submission_date, period_end_date, report_type
  - 任意フィールド: filer_name, fiscal_year, 全ての貸借対照表データ項目, candidate_contexts, candidate_keys, is_consolidated
  - Decimalを使用した精度の高い数値表現（財務データ）
  - 日付フィールド: date型（YYYY-MM-DD形式）

### 5.3 リポジトリ層（repositories/）

**ファイル構成**:
```
app/repositories/
  └── edinet_balance_sheet_repository.py
```

**リポジトリ設計方針**:
- BaseRepositoryを継承したデータアクセス層
- 非同期処理（AsyncSession）を使用
- メソッド一覧:
  - `find_latest_by_sec_code(sec_code: str)`: 指定銘柄の最新データを取得
    - period_end_dateで降順ソート、1件取得
    - 戻り値: Optional[EdinetBalanceSheet]
  - `find_by_period(sec_code: str, period_end_date: date)`: 指定銘柄・期間のデータを取得
    - UNIQUE制約により1件のみ存在
    - 戻り値: Optional[EdinetBalanceSheet]
  - `find_by_doc_id(doc_id: str)`: 文書IDでデータを取得
    - 戻り値: Optional[EdinetBalanceSheet]
  - `upsert(data: dict)`: UPSERT処理を実行（submission_date比較付き）
    - PostgreSQLの `ON CONFLICT DO UPDATE` を使用
    - UNIQUE制約: (sec_code, period_end_date)
    - submission_dateが新しい場合のみ更新（WHERE句で制御）
    - 更新対象: id, created_at以外の全カラム + updated_at自動更新
    - 戻り値: EdinetBalanceSheet
  - `get_latest_by_sec_codes(sec_codes: List[str])`: 複数銘柄の最新データを一括取得
    - IN句で複数銘柄を指定
    - 各銘柄ごとに最新のperiod_end_dateを取得
    - 戻り値: List[EdinetBalanceSheet]
  - `find_by_fiscal_year(sec_code: str, fiscal_year: int)`: 指定銘柄・会計年度のデータを取得
    - 戻り値: Optional[EdinetBalanceSheet]
  - `find_by_date_range(sec_code: str, start_date: date, end_date: date)`: 期間指定でデータを取得
    - 戻り値: List[EdinetBalanceSheet]
  - `count_by_sec_code(sec_code: str)`: 指定銘柄のレコード数を取得
    - 戻り値: int
- トランザクション管理はサービス層で実施

### 5.4 サービス層（services/）

**ファイル構成**:
```
app/services/
  ├── core/                                  # 共通処理
  │   ├── fetchers/                          # 既存の共通フェッチャー
  │   │   ├── base_fetcher.py
  │   │   ├── http_fetcher.py
  │   │   └── retry_mixin.py
  │   ├── savers/                            # 既存の共通セーバー
  │   │   ├── base_saver.py
  │   │   └── bulk_saver_mixin.py
  │   ├── validators/                        # 既存の共通バリデーター
  │   ├── converters/                        # 既存の共通コンバーター
  │   ├── parsers/                           # 新規：共通パーサー
  │   │   ├── __init__.py
  │   │   ├── base_parser.py                 # 基底パーサークラス
  │   │   └── xml_parser_mixin.py            # XMLパース用Mixin
  │   └── file_managers/                     # 新規：共通ファイル管理
  │       ├── __init__.py
  │       ├── base_file_manager.py           # 基底ファイルマネージャークラス
  │       └── temp_file_manager_mixin.py     # 一時ファイル管理用Mixin
  │
  ├── market_data/                           # 市場データ関連サービス
  │   ├── stock_price/                       # 既存：株価データ
  │   ├── stock_master/                      # 既存：銘柄マスター
  │   └── edinet/                            # 新規：EDINETデータ
  │       ├── __init__.py
  │       ├── balance_sheet/                 # 貸借対照表
  │       │   ├── __init__.py
  │       │   ├── service.py                 # メインサービス（EdinetBalanceSheetService）
  │       │   ├── fetcher.py                 # EDINETフェッチャー（EdinetDocumentFetcher）
  │       │   ├── parser.py                  # XBRLパーサー（EdinetBalanceSheetParser）
  │       │   └── file_manager.py            # ファイル管理（EdinetFileManager）
  │       └── common/                        # EDINET共通処理
  │           ├── __init__.py
  │           ├── api_client.py              # EDINET API クライアント
  │           └── xbrl_utils.py              # XBRL共通ユーティリティ
  │
  └── batch/                                 # バッチ処理
      ├── batch_execution_service.py         # 既存：バッチ実行管理
      ├── refresh_latest_stocks.py           # 既存：最新株価更新
      └── fetch_edinet_balance_sheets.py     # 新規：EDINET貸借対照表取得バッチ
```

**サービス設計方針**:

既存のプロジェクトアーキテクチャに準拠し、以下の原則に従う：
- **レイヤー分離**: fetcher（取得）、parser（解析）、saver（保存）、service（統合）を分離
- **共通処理の抽出**: 複数ドメインで使える処理は `core/` 配下に配置
- **ドメイン固有処理**: EDINET特有の処理は `market_data/edinet/` 配下に配置
- **既存パターンの踏襲**: stock_priceサービスと同様の構造を採用

---

#### 5.4.1 共通処理（core/）

**BaseParser（base_parser.py）**:
- **役割**: 各種データパーサーの基底クラス
- **継承元**: ABC（抽象基底クラス）
- **抽象メソッド**:
  - `parse(data: Any) -> Dict[str, Any]`: データを解析してdictで返す
  - `validate_data(data: Any) -> bool`: データの妥当性を検証
- **実装時の注意**:
  - 抽象メソッドは必ず実装すること
  - 例外処理は各サブクラスで実装
  - ログ出力はloggerを使用

**XMLParserMixin（xml_parser_mixin.py）**:
- **役割**: XML解析の共通処理を提供するMixin
- **依存ライブラリ**: lxml
- **提供メソッド**:
  - `parse_xml(file_path: str) -> Optional[etree._Element]`: XMLファイルをパース
  - `extract_text(element: etree._Element, xpath: str, namespaces: Dict[str, str]) -> Optional[str]`: XPathで要素テキストを抽出
- **実装時の注意**:
  - エラー時はlogger.errorでログ出力
  - 例外は捕捉してNoneを返す
  - 名前空間は呼び出し側で指定

**BaseTempFileManager（base_file_manager.py）**:
- **役割**: 一時ファイル管理の基底クラス
- **継承元**: ABC
- **初期化**:
  - `__init__(base_dir: str)`: 基底ディレクトリをPathオブジェクトに変換して保持
- **抽象メソッド**:
  - `create_temp_directory(*args, **kwargs) -> Path`: 一時ディレクトリを作成
  - `cleanup(path: Path) -> None`: 一時ファイルを削除
- **実装時の注意**:
  - ディレクトリ作成時は`parents=True, exist_ok=True`を使用
  - 削除時は存在確認を行う

---

#### 5.4.2 EDINET共通処理（market_data/edinet/common/）

**EdinetAPIClient（api_client.py）**:
- **役割**: EDINET APIとの通信を担当
- **継承**: RetryMixin（リトライ機能）
- **依存ライブラリ**: httpx（非同期HTTPクライアント）
- **初期化**:
  - `base_url`: デフォルトは "https://disclosure.edinet-fsa.go.jp/api/v2"
  - `session`: httpx.AsyncClientを作成（timeout=30.0）
- **メソッド**:
  - `search_documents(target_date: date, doc_type: int = 2) -> List[Dict]`: 指定日の書類一覧を取得
    - パラメータ: date（YYYY-MM-DD形式）、type（書類種別）
    - エンドポイント: `/documents.json`
  - `download_document(doc_id: str) -> bytes`: 書類をダウンロード
    - パラメータ: type=1（提出本文書及び監査報告書）
    - エンドポイント: `/documents/{doc_id}`
    - 戻り値: ZIPファイルのバイナリデータ
- **実装時の注意**:
  - RetryMixinの`_retry_request`メソッドを使用してリトライ処理を実装
  - API制限を考慮したレート制限（0.5秒間隔）
  - リトライは最大3回、指数バックオフ

**XBRLUtils（xbrl_utils.py）**:
- **役割**: XBRL解析の共通ユーティリティ
- **クラス変数**:
  - `NAMESPACES`: XBRL名前空間の辞書
    - xbrli, xlink, link, jpcrp_cor など
- **静的メソッド**:
  - `find_xbrl_files(extract_dir: str) -> List[str]`: XBRLファイルを探索
    - 検索パス: `{extract_dir}/XBRL/PublicDoc/*.xbrl`
  - `extract_contexts(root: etree._Element) -> Dict[str, str]`: contextを抽出
    - XPath: `//xbrli:context`
- **実装時の注意**:
  - 名前空間は必ずNAMESPACES定数を使用
  - ファイルが見つからない場合は空リストを返す

---

#### 5.4.3 貸借対照表サービス（market_data/edinet/balance_sheet/）

**EdinetBalanceSheetService（service.py）**:
- **役割**: EDINET貸借対照表の取得・解析・保存を統括
- **参考**: StockPriceServiceと同様の構造
- **依存**:
  - session: AsyncSession
  - repository: EdinetBalanceSheetRepository
  - fetcher: EdinetDocumentFetcher
  - parser: EdinetBalanceSheetParser
  - file_manager: EdinetFileManager
- **メソッド**:
  - `fetch_and_save_single(doc_id: str, sec_code: str) -> List[EdinetBalanceSheetRead]`: 1件の書類を取得・解析・保存（5年分）
    - 処理フロー: ダウンロード → 解析（5年分） → 各年度をUPSERT → クリーンアップ
    - エラー時もクリーンアップを実行（finally句）
    - 戻り値: 保存に成功した年度のデータリスト（最大5件）
  - `upsert_balance_sheet(data: EdinetBalanceSheetCreate) -> EdinetBalanceSheetRead`: UPSERT処理
    - repository.upsert呼び出し → session.commit
  - `get_latest_by_sec_code(sec_code: str) -> Optional[EdinetBalanceSheetLatest]`: 最新データ取得
  - `get_by_period(sec_code: str, period_end_date: date) -> Optional[EdinetBalanceSheetRead]`: 期間指定取得
  - `get_annual_data(sec_code: str, limit: int = 10) -> List[EdinetBalanceSheetRead]`: 年次データ取得
  - `get_multiple_latest(sec_codes: List[str]) -> List[EdinetBalanceSheetLatest]`: 複数銘柄の最新データ取得
- **実装時の注意**:
  - 結果はスキーマクラス（Read, Latest）でバリデーション
  - エラー時はログ出力とクリーンアップ
  - トランザクションは明示的にコミット
  - 5年分のデータをループで処理し、各年度ごとにUPSERT実行
  - 一部の年度でエラーが発生しても他の年度の処理は継続

**EdinetDocumentFetcher（fetcher.py）**:
- **役割**: EDINET書類のダウンロード・解凍
- **継承**: BaseFetcher
- **依存**:
  - api_client: EdinetAPIClient
  - temp_dir: 一時ディレクトリのパス（デフォルト: "work/edinet_temp"）
- **メソッド**:
  - `fetch(doc_id: str) -> Path`: 1件取得（BaseFetcherインターフェース実装）
  - `fetch_batch(doc_ids: List[str]) -> List[Path]`: 複数並列取得
    - asyncio.gatherで並列実行
  - `download_document(doc_id: str) -> Path`: ダウンロード・解凍の実処理
    - ZIPダウンロード → 保存 → 解凍
    - 戻り値: 解凍先ディレクトリ
  - `search_documents(target_date: date, doc_type: int = 2) -> List[Dict]`: 書類検索
  - `validate_identifier(identifier: str) -> bool`: doc_idの形式検証（8文字）
- **実装時の注意**:
  - ZIPファイルはzipfileモジュールで解凍
  - ディレクトリ作成は親ディレクトリも含めて作成
  - エラー時は例外を送出

**EdinetBalanceSheetParser（parser.py）**:
- **役割**: XBRLファイルから貸借対照表データを抽出（当期+過去4年分の計5年分）
- **継承**: BaseParser, XMLParserMixin
- **依存**: XBRLUtils（名前空間定義）
- **メソッド**:
  - `parse(xbrl_file_path: str) -> List[Dict[str, Any]]`: メイン解析処理
    - XML解析 → バリデーション → 各年度のデータ抽出（5年分）
    - 戻り値: 各年度のデータを含む辞書のリスト（最大5件）
  - `parse_single_year(root: etree._Element, year_type: str) -> Optional[Dict[str, Any]]`: 単一年度の解析
    - year_type: "CurrentYear", "Prior1Year", "Prior2Year", "Prior3Year", "Prior4Year"
    - 各年度のコンテキストを使用してデータ抽出 → 指標計算
  - `validate_data(root: etree._Element) -> bool`: XBRL構造の妥当性検証
    - 必須要素（context, TotalAssetsなど）の存在確認
  - `extract_assets(root: etree._Element, contexts: Dict, year_type: str) -> Dict[str, Any]`: 資産項目抽出
    - total_assets, current_assets, non_current_assets, cash_and_equivalents
    - year_typeに応じた適切なコンテキスト（CurrentYearInstant, Prior1YearInstantなど）を使用
  - `extract_liabilities(root: etree._Element, contexts: Dict, year_type: str) -> Dict[str, Any]`: 負債項目抽出
    - total_liabilities, current_liabilities, non_current_liabilities, short_term_loans, long_term_loans
    - year_typeに応じた適切なコンテキストを使用
  - `extract_equity(root: etree._Element, contexts: Dict, year_type: str) -> Dict[str, Any]`: 純資産項目抽出
    - total_equity, shareholders_equity, retained_earnings
    - year_typeに応じた適切なコンテキストを使用
  - `calculate_metrics(assets: Dict, liabilities: Dict, equity: Dict) -> Dict[str, Any]`: 財務指標計算
    - equity_to_asset_ratio（自己資本比率）, bpsなど
  - `determine_consolidation(root: etree._Element, year_type: str) -> Optional[bool]`: 連結/単体判定
    - contextIDに"Consolidated"または"NonConsolidated"が含まれるか確認
  - `get_period_end_date(root: etree._Element, year_type: str) -> Optional[date]`: 決算期末日の取得
    - 各年度のコンテキストから期末日を抽出
  - `_extract_numeric(root: etree._Element, tag: str, year_type: str) -> Optional[float]`: 数値抽出（共通処理）
    - year_typeに応じた適切なコンテキストを使用
- **実装時の注意**:
  - XPath検索時は必ずXBRLUtils.NAMESPACESを使用
  - 数値変換エラーはNoneを返す
  - candidate_contexts, candidate_keysの記録（デバッグ用）
  - 各年度のデータが取得できない場合はスキップ（エラーにしない）
  - 戻り値は実際に取得できた年度のデータのみを含むリスト

**EdinetFileManager（file_manager.py）**:
- **役割**: EDINET一時ファイルの管理
- **継承**: BaseTempFileManager
- **初期化**: base_dir（デフォルト: "work/edinet_temp"）
- **メソッド**:
  - `create_temp_directory(doc_id: str) -> Path`: 一時ディレクトリ作成
  - `cleanup(path: Path) -> None`: ファイル削除（shutil.rmtree使用）
  - `find_xbrl_file(extract_dir: Path) -> Optional[str]`: XBRLファイル探索
    - XBRLUtils.find_xbrl_files使用
  - `cleanup_old_files(days: int = 7) -> int`: 古いファイル削除
    - 指定日数以前のディレクトリを削除
    - 戻り値: 削除件数
- **実装時の注意**:
  - cleanup実行前に存在確認
  - cleanup_old_filesは定期実行（cron等）

---

#### 5.4.4 バッチ処理（batch/）

**FetchEdinetBalanceSheets（fetch_edinet_balance_sheets.py）**:
- **役割**: EDINET貸借対照表取得バッチのメイン処理
- **参考**: refresh_latest_stocksと同様の構造
- **クラス変数**:
  - `BATCH_TYPE = "edinet_balance_sheet_fetch"`
- **依存**:
  - session: AsyncSession
  - batch_service: BatchExecutionService（進捗管理）
  - balance_sheet_service: EdinetBalanceSheetService
  - fetcher: EdinetDocumentFetcher
- **メソッド**:
  - `execute(start_date: date, end_date: date) -> Dict`: バッチ実行
    - 処理フロー:
      1. バッチ実行レコード作成（status='running'）
      2. 書類一覧取得（期間内の全日付をループ）
      3. 各書類を処理（fetch_and_save_single呼び出し）
         - 1つの書類から5年分のデータを取得・保存
         - 取得成功した年度数を集計
      4. 10件ごとに進捗更新
      5. 完了処理（status='completed'）
    - エラー時: fail_batch_execution呼び出し
  - `_search_documents(start_date: date, end_date: date) -> List[Dict]`: 期間内の書類検索
    - 日付をループしてsearch_documents呼び出し
- **実装時の注意**:
  - エラー時も処理継続（try-exceptで個別処理）
  - 進捗更新は定期的に実行（10件ごと）
  - ログ出力はloggerを使用
  - 戻り値は実行結果サマリー（total_documents, total_years_saved, successful_documents, failed_documents）
  - 1つの書類で5年分のデータを取得するため、保存されたレコード数は書類数の最大5倍になる

---

## 6. パフォーマンス最適化

### 6.1 インデックス設計

**高頻度クエリ**:
1. 銘柄コードによる検索: `idx_edinet_bs_sec_code`
2. 期間による検索: `idx_edinet_bs_period_end`
3. 複合検索（最頻出）: `idx_edinet_bs_sec_period (sec_code, period_end_date DESC)`
4. UNIQUE制約: `uq_edinet_bs_sec_period (sec_code, period_end_date)` - UPSERT処理で使用

**インデックスサイズ見積もり**:
- 10,000銘柄 × 10年分 = 100,000レコード
- インデックスサイズ: 約10-20MB（問題なし）

### 6.2 クエリ最適化

**推奨クエリパターン**:
```sql
-- 最新データ取得（直近の決算期）
SELECT * FROM edinet_balance_sheets
WHERE sec_code = '7203'
ORDER BY period_end_date DESC
LIMIT 1;

-- 年次データ取得（過去10年分）
SELECT * FROM edinet_balance_sheets
WHERE sec_code = '7203'
ORDER BY period_end_date DESC
LIMIT 10;

-- 一括取得（IN句使用、各銘柄の最新）
WITH ranked_data AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY sec_code ORDER BY period_end_date DESC) as rn
  FROM edinet_balance_sheets
  WHERE sec_code IN ('7203', '6758', '8306')
)
SELECT * FROM ranked_data WHERE rn = 1;
```

### 6.3 バッチサイズ

| 処理         | 推奨バッチサイズ | 理由                               |
| ------------ | ---------------- | ---------------------------------- |
| ダウンロード | 50-100件         | API制限考慮                        |
| XBRL解析     | 100-200件        | メモリ消費とのバランス             |
| DB挿入       | 500-1000件       | トランザクションオーバーヘッド削減 |

---

## 7. 運用・保守

### 7.1 マイグレーション手順

**新規テーブル作成手順**:
1. マイグレーションファイル生成
   - コマンド: `poetry run alembic revision --autogenerate -m "add_edinet_balance_sheets_table"`
   - モデル定義から自動的にマイグレーションファイルが生成される
2. マイグレーション適用
   - コマンド: `poetry run alembic upgrade head`
   - データベースにテーブル・インデックスが作成される
3. マイグレーションファイルの内容:
   - テーブル作成（edinet_balance_sheets）
   - インデックス作成
   - UNIQUE制約の定義

### 7.2 データメンテナンス

**メンテナンスタスク**:

1. **バッチ実行履歴の確認**
   ```sql
   -- 最近のバッチ実行履歴
   SELECT id, batch_type, status, total_stocks, successful_stocks, failed_stocks,
          start_time, end_time
   FROM batch_executions
   WHERE batch_type = 'edinet_balance_sheet_fetch'
   ORDER BY start_time DESC
   LIMIT 10;
   ```

2. **エラーログの確認**
   - ログファイル（`logs/edinet_processing/{date}.log`）を確認
   - 頻発するエラーパターンを分析

3. **一時ファイルのクリーンアップ**（定期実行）
   - 一時ディレクトリ（`work/edinet_temp/`）の古いファイルを削除
   - 7日以上前のファイルは自動削除

4. **重複データのチェック**
   ```sql
   -- 同一年度に複数レコードがないか確認（UNIQUE制約で防止されているが念のため）
   SELECT sec_code, period_end_date, COUNT(*)
   FROM edinet_balance_sheets
   GROUP BY sec_code, period_end_date
   HAVING COUNT(*) > 1;
   ```

5. **インデックス再構築**（年次）
   ```sql
   REINDEX TABLE edinet_balance_sheets;
   ```

### 7.3 監視項目

| 監視項目           | 閾値    | アクション                             |
| ------------------ | ------- | -------------------------------------- |
| 解析失敗率         | > 10%   | エラーログ調査、XBRL解析ロジック見直し |
| バッチ処理時間     | > 6時間 | 並列度の調整、API制限の確認            |
| クエリ応答時間     | > 500ms | インデックス見直し                     |
| DBディスク使用量   | > 80%   | データアーカイブ                       |
| 一時ディスク使用量 | > 10GB  | クリーンアップ処理の実行               |

---

## 8. セキュリティ考慮事項

1. **API キー管理**
   - 環境変数で管理（`.env` ファイル）
   - コミットしない（`.gitignore` に追加）

2. **ファイルアクセス制御**
   - ダウンロードファイルの保存先を制限
   - パストラバーサル対策

3. **データアクセス制御**
   - 最小権限の原則（データベースユーザー）
   - 読み取り専用ユーザーの作成

4. **ログ管理**
   - 個人情報を含むログは暗号化
   - ログローテーション設定

---

## 9. 将来拡張性

**想定される拡張**:
1. **四半期報告書対応**
   - `report_type` カラムで区別
   - 同じテーブル構造を再利用

2. **損益計算書・キャッシュフロー**
   - 別テーブルとして追加
   - `edinet_documents` との1:N関係を維持

3. **銀行向けタグ対応**
   - 別カラムとして追加
   - `is_bank_format` フラグで区別

4. **自動リバランス機能**
   - 最新データの自動チェック
   - 日次バッチで古いデータを検出・更新

5. **データ品質スコアリング**
  - 解析結果の品質管理の強化（解析ログやメタ情報の整備）
   - 機械学習による品質予測

---

**作成日**: 2026-01-28
**作成者**: GitHub Copilot
**バージョン**: 1.0
