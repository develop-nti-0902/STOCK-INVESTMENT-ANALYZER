-- =============================================================================
-- [DEPRECATED] このファイルは参考用として保持されています
-- =============================================================================
-- 現在のデータベーススキーマはAlembicマイグレーションで管理されています。
-- スキーマ変更はAlembicリビジョンファイルを作成してください。
--
-- 初期設定: alembic/versions/4e581533f2e4_initial_database_schema.py
-- マイグレーション適用: alembic upgrade head
-- =============================================================================

-- create_management_tables.sql
-- 管理データテーブルを作成するSQLスクリプト
-- 作成されるテーブル: stock_master, stock_master_updates,
--                  batch_executions, batch_execution_details

BEGIN;

-- 銘柄マスタ
CREATE TABLE IF NOT EXISTS stock_master (
  id SERIAL PRIMARY KEY,
  stock_code VARCHAR(10) NOT NULL UNIQUE,
  stock_name VARCHAR(100) NOT NULL,
  market_category VARCHAR(50),
  sector_code_33 VARCHAR(10),
  sector_name_33 VARCHAR(100),
  sector_code_17 VARCHAR(10),
  sector_name_17 VARCHAR(100),
  scale_code VARCHAR(10),
  scale_category VARCHAR(50),
  data_date VARCHAR(8),
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stock_master_code ON stock_master (stock_code);
CREATE INDEX IF NOT EXISTS idx_stock_master_active ON stock_master (is_active);
CREATE INDEX IF NOT EXISTS idx_stock_master_market ON stock_master (market_category);
CREATE INDEX IF NOT EXISTS idx_stock_master_sector_33 ON stock_master (sector_code_33);

-- 銘柄マスタ更新履歴
CREATE TABLE IF NOT EXISTS stock_master_updates (
  id SERIAL PRIMARY KEY,
  update_type VARCHAR(20) NOT NULL,
  total_stocks INTEGER NOT NULL,
  added_stocks INTEGER DEFAULT 0,
  updated_stocks INTEGER DEFAULT 0,
  removed_stocks INTEGER DEFAULT 0,
  status VARCHAR(20) NOT NULL,
  error_message TEXT,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  completed_at TIMESTAMP WITH TIME ZONE
);

-- バッチ実行サマリ
CREATE TABLE IF NOT EXISTS batch_executions (
  id SERIAL PRIMARY KEY,
  batch_type VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL,
  total_stocks INTEGER NOT NULL,
  processed_stocks INTEGER DEFAULT 0,
  successful_stocks INTEGER DEFAULT 0,
  failed_stocks INTEGER DEFAULT 0,
  start_time TIMESTAMP WITH TIME ZONE DEFAULT now(),
  end_time TIMESTAMP WITH TIME ZONE,
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_batch_executions_status ON batch_executions (status);
CREATE INDEX IF NOT EXISTS idx_batch_executions_batch_type ON batch_executions (batch_type);
CREATE INDEX IF NOT EXISTS idx_batch_executions_start_time ON batch_executions (start_time);

-- バッチ実行詳細（各銘柄ごとの詳細）
CREATE TABLE IF NOT EXISTS batch_execution_details (
  id SERIAL PRIMARY KEY,
  batch_execution_id INTEGER NOT NULL REFERENCES batch_executions(id) ON DELETE CASCADE,
  stock_code VARCHAR(10) NOT NULL,
  status VARCHAR(20) NOT NULL,
  start_time TIMESTAMP WITH TIME ZONE,
  end_time TIMESTAMP WITH TIME ZONE,
  error_message TEXT,
  records_inserted INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_batch_execution_details_batch_id
    ON batch_execution_details (batch_execution_id);
CREATE INDEX IF NOT EXISTS idx_batch_execution_details_status
    ON batch_execution_details (status);
CREATE INDEX IF NOT EXISTS idx_batch_execution_details_stock_code
    ON batch_execution_details (stock_code);
CREATE INDEX IF NOT EXISTS idx_batch_execution_details_batch_stock
    ON batch_execution_details (batch_execution_id, stock_code);

-- テーブルの所有者を stock_user に変更し、権限を付与
-- これにより、アプリケーションユーザーがテーブルにアクセスできるようになります
DO $$
DECLARE
    db_user TEXT := current_setting('db_user', TRUE);
BEGIN
    IF db_user IS NULL OR db_user = '' THEN
        -- 環境変数が設定されていない場合はデフォルト値を使用
        db_user := 'stock_user';
    END IF;

    -- テーブルの所有者を変更
    EXECUTE format('ALTER TABLE stock_master OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE stock_master_updates OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE batch_executions OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE batch_execution_details OWNER TO %I', db_user);

    -- シーケンスの所有者も変更
    EXECUTE format('ALTER SEQUENCE stock_master_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE stock_master_updates_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE batch_executions_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE batch_execution_details_id_seq OWNER TO %I', db_user);

    -- 明示的に権限を付与
    EXECUTE format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %I', db_user);
    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO %I', db_user);
END
$$;

COMMIT;

-- 補足:
-- - このスクリプトは `docs/architecture/.../data_storage_layer.md` の管理データテーブル定義に準拠しています。
-- - ライブDBへ適用する場合、必要に応じてインデックス作成を `CONCURRENTLY` で行うなど運用上の配慮を行ってください。
