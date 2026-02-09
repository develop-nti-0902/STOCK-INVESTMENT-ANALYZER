-- =============================================================================
-- [DEPRECATED] このファイルは参考用として保持されています
-- =============================================================================
-- 現在のデータベーススキーマはAlembicマイグレーションで管理されています。
-- スキーマ変更はAlembicリビジョンファイルを作成してください。
--
-- 初期設定: alembic/versions/4e581533f2e4_initial_database_schema.py
-- マイグレーション適用: alembic upgrade head
-- =============================================================================

BEGIN;

-- users テーブル
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

-- user_transactions テーブル
CREATE TABLE IF NOT EXISTS user_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    transaction_type VARCHAR(4) NOT NULL CHECK (transaction_type IN ('BUY','SELL')),
    quantity NUMERIC(15,4) NOT NULL,
    price NUMERIC(15,2) NOT NULL,
    total_amount NUMERIC(20,2) NOT NULL,
    commission NUMERIC(10,2) DEFAULT 0,
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
);

CREATE INDEX IF NOT EXISTS idx_user_transactions_user_symbol_date ON user_transactions (user_id, symbol, transaction_date);

-- user_portfolios テーブル
CREATE TABLE IF NOT EXISTS user_portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity NUMERIC(15,4) NOT NULL DEFAULT 0,
    average_price NUMERIC(15,2) NOT NULL DEFAULT 0,
    total_cost NUMERIC(20,2) NOT NULL DEFAULT 0,
    stop_loss_price NUMERIC(15,2),
    take_profit_price NUMERIC(15,2),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_user_portfolios_user_id ON user_portfolios (user_id);

-- 所有者変更とシーケンス権限付与
DO $$
DECLARE
    db_user TEXT := current_setting('db_user', TRUE);
BEGIN
    IF db_user IS NULL OR db_user = '' THEN
        db_user := 'stock_user';
    END IF;

    EXECUTE format('ALTER TABLE users OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE user_transactions OWNER TO %I', db_user);
    EXECUTE format('ALTER TABLE user_portfolios OWNER TO %I', db_user);

    EXECUTE format('ALTER SEQUENCE users_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE user_transactions_id_seq OWNER TO %I', db_user);
    EXECUTE format('ALTER SEQUENCE user_portfolios_id_seq OWNER TO %I', db_user);

    EXECUTE format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %I', db_user);
    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO %I', db_user);
END
$$;

COMMIT;
