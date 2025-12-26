-- create_stock_tables.sql
-- 株価データ（各時間足）用テーブルを作成するSQLスクリプト
-- 作成されるテーブル: stocks_1m, stocks_5m, stocks_15m, stocks_30m, stocks_1h,
--                  stocks_1d, stocks_1wk, stocks_1mo
-- 制約・インデックスは `docs/architecture/.../data_storage_layer.md` の仕様に従います。

BEGIN;

-- 価格は精度を保つため NUMERIC 型を使用しています。必要に応じて精度を指定してください（例: NUMERIC(14,4)）。

-- 分・時間足テーブル（日時は TIMESTAMP 型を使用）
CREATE TABLE IF NOT EXISTS stocks_1m (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(10) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  open NUMERIC(14,4) NOT NULL,
  high NUMERIC(14,4) NOT NULL,
  low NUMERIC(14,4) NOT NULL,
  close NUMERIC(14,4) NOT NULL,
  adj_close NUMERIC(14,4),
  volume BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT uq_stocks_1m_symbol_timestamp UNIQUE (symbol, timestamp),
  CONSTRAINT chk_stocks_1m_non_negative_prices CHECK (open >= 0 AND high >= 0 AND low >= 0 AND close >= 0),
  CONSTRAINT chk_stocks_1m_high_low_logic CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
  CONSTRAINT chk_stocks_1m_volume_non_negative CHECK (volume >= 0),
  CONSTRAINT fk_stocks_1m_symbol_master FOREIGN KEY (symbol) REFERENCES stock_master(stock_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stocks_1m_symbol ON stocks_1m (symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_1m_timestamp ON stocks_1m (timestamp);
CREATE INDEX IF NOT EXISTS idx_stocks_1m_symbol_timestamp_desc ON stocks_1m (symbol, timestamp DESC);

CREATE TABLE IF NOT EXISTS stocks_5m (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(10) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  open NUMERIC(14,4) NOT NULL,
  high NUMERIC(14,4) NOT NULL,
  low NUMERIC(14,4) NOT NULL,
  close NUMERIC(14,4) NOT NULL,
  adj_close NUMERIC(14,4),
  volume BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT uq_stocks_5m_symbol_timestamp UNIQUE (symbol, timestamp),
  CONSTRAINT chk_stocks_5m_non_negative_prices CHECK (open >= 0 AND high >= 0 AND low >= 0 AND close >= 0),
  CONSTRAINT chk_stocks_5m_high_low_logic CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
  CONSTRAINT chk_stocks_5m_volume_non_negative CHECK (volume >= 0),
  CONSTRAINT fk_stocks_5m_symbol_master FOREIGN KEY (symbol) REFERENCES stock_master(stock_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stocks_5m_symbol ON stocks_5m (symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_5m_timestamp ON stocks_5m (timestamp);
CREATE INDEX IF NOT EXISTS idx_stocks_5m_symbol_timestamp_desc ON stocks_5m (symbol, timestamp DESC);

CREATE TABLE IF NOT EXISTS stocks_15m (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(10) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  open NUMERIC(14,4) NOT NULL,
  high NUMERIC(14,4) NOT NULL,
  low NUMERIC(14,4) NOT NULL,
  close NUMERIC(14,4) NOT NULL,
  adj_close NUMERIC(14,4),
  volume BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT uq_stocks_15m_symbol_timestamp UNIQUE (symbol, timestamp),
  CONSTRAINT chk_stocks_15m_non_negative_prices CHECK (open >= 0 AND high >= 0 AND low >= 0 AND close >= 0),
  CONSTRAINT chk_stocks_15m_high_low_logic CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
  CONSTRAINT chk_stocks_15m_volume_non_negative CHECK (volume >= 0),
  CONSTRAINT fk_stocks_15m_symbol_master FOREIGN KEY (symbol) REFERENCES stock_master(stock_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stocks_15m_symbol ON stocks_15m (symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_15m_timestamp ON stocks_15m (timestamp);
CREATE INDEX IF NOT EXISTS idx_stocks_15m_symbol_timestamp_desc ON stocks_15m (symbol, timestamp DESC);

CREATE TABLE IF NOT EXISTS stocks_30m (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(10) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  open NUMERIC(14,4) NOT NULL,
  high NUMERIC(14,4) NOT NULL,
  low NUMERIC(14,4) NOT NULL,
  close NUMERIC(14,4) NOT NULL,
  adj_close NUMERIC(14,4),
  volume BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT uq_stocks_30m_symbol_timestamp UNIQUE (symbol, timestamp),
  CONSTRAINT chk_stocks_30m_non_negative_prices CHECK (open >= 0 AND high >= 0 AND low >= 0 AND close >= 0),
  CONSTRAINT chk_stocks_30m_high_low_logic CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
  CONSTRAINT chk_stocks_30m_volume_non_negative CHECK (volume >= 0),
  CONSTRAINT fk_stocks_30m_symbol_master FOREIGN KEY (symbol) REFERENCES stock_master(stock_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stocks_30m_symbol ON stocks_30m (symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_30m_timestamp ON stocks_30m (timestamp);
CREATE INDEX IF NOT EXISTS idx_stocks_30m_symbol_timestamp_desc ON stocks_30m (symbol, timestamp DESC);

CREATE TABLE IF NOT EXISTS stocks_1h (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(10) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  open NUMERIC(14,4) NOT NULL,
  high NUMERIC(14,4) NOT NULL,
  low NUMERIC(14,4) NOT NULL,
  close NUMERIC(14,4) NOT NULL,
  adj_close NUMERIC(14,4),
  volume BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT uq_stocks_1h_symbol_timestamp UNIQUE (symbol, timestamp),
  CONSTRAINT chk_stocks_1h_non_negative_prices CHECK (open >= 0 AND high >= 0 AND low >= 0 AND close >= 0),
  CONSTRAINT chk_stocks_1h_high_low_logic CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
  CONSTRAINT chk_stocks_1h_volume_non_negative CHECK (volume >= 0),
  CONSTRAINT fk_stocks_1h_symbol_master FOREIGN KEY (symbol) REFERENCES stock_master(stock_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stocks_1h_symbol ON stocks_1h (symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_1h_timestamp ON stocks_1h (timestamp);
CREATE INDEX IF NOT EXISTS idx_stocks_1h_symbol_timestamp_desc ON stocks_1h (symbol, timestamp DESC);

-- 日足・週足・月足テーブル（日時は TIMESTAMP 型を使用）
CREATE TABLE IF NOT EXISTS stocks_1d (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(10) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  open NUMERIC(14,4) NOT NULL,
  high NUMERIC(14,4) NOT NULL,
  low NUMERIC(14,4) NOT NULL,
  close NUMERIC(14,4) NOT NULL,
  adj_close NUMERIC(14,4),
  volume BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT uq_stocks_1d_symbol_timestamp UNIQUE (symbol, timestamp),
  CONSTRAINT chk_stocks_1d_non_negative_prices CHECK (open >= 0 AND high >= 0 AND low >= 0 AND close >= 0),
  CONSTRAINT chk_stocks_1d_high_low_logic CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
  CONSTRAINT chk_stocks_1d_volume_non_negative CHECK (volume >= 0),
  CONSTRAINT fk_stocks_1d_symbol_master FOREIGN KEY (symbol) REFERENCES stock_master(stock_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stocks_1d_symbol ON stocks_1d (symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_1d_timestamp ON stocks_1d (timestamp);
CREATE INDEX IF NOT EXISTS idx_stocks_1d_symbol_timestamp_desc ON stocks_1d (symbol, timestamp DESC);

CREATE TABLE IF NOT EXISTS stocks_1wk (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(10) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  open NUMERIC(14,4) NOT NULL,
  high NUMERIC(14,4) NOT NULL,
  low NUMERIC(14,4) NOT NULL,
  close NUMERIC(14,4) NOT NULL,
  adj_close NUMERIC(14,4),
  volume BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT uq_stocks_1wk_symbol_timestamp UNIQUE (symbol, timestamp),
  CONSTRAINT chk_stocks_1wk_non_negative_prices CHECK (open >= 0 AND high >= 0 AND low >= 0 AND close >= 0),
  CONSTRAINT chk_stocks_1wk_high_low_logic CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
  CONSTRAINT chk_stocks_1wk_volume_non_negative CHECK (volume >= 0),
  CONSTRAINT fk_stocks_1wk_symbol_master FOREIGN KEY (symbol) REFERENCES stock_master(stock_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stocks_1wk_symbol ON stocks_1wk (symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_1wk_timestamp ON stocks_1wk (timestamp);
CREATE INDEX IF NOT EXISTS idx_stocks_1wk_symbol_timestamp_desc ON stocks_1wk (symbol, timestamp DESC);

CREATE TABLE IF NOT EXISTS stocks_1mo (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(10) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  open NUMERIC(14,4) NOT NULL,
  high NUMERIC(14,4) NOT NULL,
  low NUMERIC(14,4) NOT NULL,
  close NUMERIC(14,4) NOT NULL,
  adj_close NUMERIC(14,4),
  volume BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT uq_stocks_1mo_symbol_timestamp UNIQUE (symbol, timestamp),
  CONSTRAINT chk_stocks_1mo_non_negative_prices CHECK (open >= 0 AND high >= 0 AND low >= 0 AND close >= 0),
  CONSTRAINT chk_stocks_1mo_high_low_logic CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
  CONSTRAINT chk_stocks_1mo_volume_non_negative CHECK (volume >= 0),
  CONSTRAINT fk_stocks_1mo_symbol_master FOREIGN KEY (symbol) REFERENCES stock_master(stock_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stocks_1mo_symbol ON stocks_1mo (symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_1mo_timestamp ON stocks_1mo (timestamp);
CREATE INDEX IF NOT EXISTS idx_stocks_1mo_symbol_timestamp_desc ON stocks_1mo (symbol, timestamp DESC);

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
    EXECUTE format('ALTER TABLE stocks_1m OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE stocks_5m OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE stocks_15m OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE stocks_30m OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE stocks_1h OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE stocks_1d OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE stocks_1wk OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE stocks_1mo OWNER TO %I', db_user);

    -- シーケンスの所有者も変更
    EXECUTE format('ALTER SEQUENCE stocks_1m_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE stocks_5m_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE stocks_15m_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE stocks_30m_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE stocks_1h_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE stocks_1d_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE stocks_1wk_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE stocks_1mo_id_seq OWNER TO %I', db_user);

    -- 明示的に権限を付与
    EXECUTE format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %I', db_user);
    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO %I', db_user);
END
$$;

COMMIT;

-- 補足:
-- - このスクリプトはアーキテクチャ仕様に基づく単純なリレーショナルテーブルを作成します。
-- - 大規模運用ではテーブルパーティショニング（symbol別または時間範囲別）を検討してください。
-- - ライブDBへ適用する場合、インデックス作成は `CONCURRENTLY` を使うことを検討してください。
-- - 固定小数点の精度が必要な場合は NUMERIC(precision,scale) の指定を行ってください（例: NUMERIC(14,4)）。
-- - 実行例:
--   psql -h <DB_HOST> -p <DB_PORT> -U <DB_USER> -d <DB_NAME> -f scripts/databaseSetup/sql/create_stock_tables.sql
