-- drop_user_tables.sql
-- Issue #166: ユーザー / 取引履歴 / ポートフォリオ用テーブル削除

-- Drop in order respecting FK constraints
DROP TABLE IF EXISTS user_portfolios;
DROP TABLE IF EXISTS user_transactions;
DROP TABLE IF EXISTS users;
