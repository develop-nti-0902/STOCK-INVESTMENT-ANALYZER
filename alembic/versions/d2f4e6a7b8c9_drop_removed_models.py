"""drop removed models: stock analyst and balance sheet tables.

Revision ID: d2f4e6a7b8c9
Revises: c1f9d2b3e4f5
Create Date: 2026-02-11 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2f4e6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c1f9d2b3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop tables for removed models."""
    # Use IF EXISTS semantics to be resilient
    op.execute("DROP TABLE IF EXISTS stock_analyst_recommendations;")
    op.execute("DROP TABLE IF EXISTS stock_balance_sheet_annual;")
    op.execute("DROP TABLE IF EXISTS stock_balance_sheet_quarterly;")
    op.execute("DROP TABLE IF EXISTS stock_basic_info;")
    op.execute("DROP TABLE IF EXISTS stock_cashflow_annual;")
    op.execute("DROP TABLE IF EXISTS stock_cashflow_quarterly;")
    op.execute("DROP TABLE IF EXISTS stock_dividends;")
    op.execute("DROP TABLE IF EXISTS stock_financial_info;")
    op.execute("DROP TABLE IF EXISTS stock_financials_annual;")
    op.execute("DROP TABLE IF EXISTS stock_financials_quarterly;")
    op.execute("DROP TABLE IF EXISTS stock_holders_institutional;")
    op.execute("DROP TABLE IF EXISTS stock_holders_mutualfund;")
    op.execute("DROP TABLE IF EXISTS stock_insider_transactions;")
    op.execute("DROP TABLE IF EXISTS stock_shares_outstanding;")
    op.execute("DROP TABLE IF EXISTS stock_splits;")


def downgrade() -> None:
    """Recreate the dropped tables (best-effort schema matching previous models)."""
    # stock_analyst_recommendations
    op.create_table(
        "stock_analyst_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("strong_buy", sa.Integer(), nullable=True),
        sa.Column("buy", sa.Integer(), nullable=True),
        sa.Column("hold", sa.Integer(), nullable=True),
        sa.Column("sell", sa.Integer(), nullable=True),
        sa.Column("strong_sell", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "idx_recommendations_symbol_period",
        "stock_analyst_recommendations",
        ["symbol", "period"],
        unique=False,
    )
    op.create_index(
        "uq_recommendations_symbol_period_source",
        "stock_analyst_recommendations",
        ["symbol", "period", "source"],
        unique=True,
    )

    # stock_balance_sheet_annual
    op.create_table(
        "stock_balance_sheet_annual",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("total_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("current_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("non_current_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("total_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("current_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("non_current_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("total_equity", sa.Numeric(20, 2), nullable=True),
        sa.Column("cash_and_equivalents", sa.Numeric(20, 2), nullable=True),
        sa.Column("retained_earnings", sa.Numeric(20, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "idx_stock_balancesheet_symbol", "stock_balance_sheet_annual", ["symbol"], unique=False
    )
    op.create_index(
        "idx_stock_balancesheet_year", "stock_balance_sheet_annual", ["fiscal_year"], unique=False
    )

    # stock_balance_sheet_quarterly
    op.create_table(
        "stock_balance_sheet_quarterly",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("fiscal_quarter", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("total_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("current_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("non_current_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("total_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("current_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("non_current_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("total_equity", sa.Numeric(20, 2), nullable=True),
        sa.Column("cash_and_equivalents", sa.Numeric(20, 2), nullable=True),
        sa.Column("retained_earnings", sa.Numeric(20, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "idx_stock_bsq_symbol", "stock_balance_sheet_quarterly", ["symbol"], unique=False
    )
    op.create_index(
        "idx_stock_bsq_year_quarter",
        "stock_balance_sheet_quarterly",
        ["fiscal_year", "fiscal_quarter"],
        unique=False,
    )
    op.create_index(
        "uq_stock_bsq_symbol_year_quarter",
        "stock_balance_sheet_quarterly",
        ["symbol", "fiscal_year", "fiscal_quarter"],
        unique=True,
    )

    # stock_dividends
    op.create_table(
        "stock_dividends",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("declaration_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("frequency", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_stock_dividends_symbol", "stock_dividends", ["symbol"], unique=False)
    op.create_index("idx_stock_dividends_exdate", "stock_dividends", ["ex_date"], unique=False)
    op.create_index(
        "idx_stock_dividends_payment", "stock_dividends", ["payment_date"], unique=False
    )

    # stock_financial_info
    op.create_table(
        "stock_financial_info",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("total_revenue", sa.Numeric(20, 2), nullable=True),
        sa.Column("gross_profit", sa.Numeric(20, 2), nullable=True),
        sa.Column("operating_income", sa.Numeric(20, 2), nullable=True),
        sa.Column("net_income", sa.Numeric(20, 2), nullable=True),
        sa.Column("basic_eps", sa.Numeric(18, 4), nullable=True),
        sa.Column("diluted_eps", sa.Numeric(18, 4), nullable=True),
        sa.Column("total_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("total_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("cash_and_cash_equivalents", sa.Numeric(20, 2), nullable=True),
        sa.Column("operating_cashflow", sa.Numeric(20, 2), nullable=True),
        sa.Column("free_cashflow", sa.Numeric(20, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_stock_financial_symbol", "stock_financial_info", ["symbol"], unique=False)
    op.create_index(
        "idx_stock_financial_fiscal", "stock_financial_info", ["fiscal_year"], unique=False
    )
    op.create_index(
        "idx_stock_financial_period", "stock_financial_info", ["period_end"], unique=False
    )

    # stock_financials_annual
    op.create_table(
        "stock_financials_annual",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("revenue", sa.Numeric(20, 2), nullable=True),
        sa.Column("operating_income", sa.Numeric(20, 2), nullable=True),
        sa.Column("net_income", sa.Numeric(20, 2), nullable=True),
        sa.Column("basic_eps", sa.Numeric(18, 4), nullable=True),
        sa.Column("roe", sa.Numeric(6, 4), nullable=True),
        sa.Column("roa", sa.Numeric(6, 4), nullable=True),
        sa.Column("total_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("total_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("dividends_per_share", sa.Numeric(18, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_stock_finann_symbol", "stock_financials_annual", ["symbol"], unique=False)
    op.create_index(
        "idx_stock_finann_year", "stock_financials_annual", ["fiscal_year"], unique=False
    )

    # stock_financials_quarterly
    op.create_table(
        "stock_financials_quarterly",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("fiscal_quarter", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("revenue", sa.Numeric(20, 2), nullable=True),
        sa.Column("operating_income", sa.Numeric(20, 2), nullable=True),
        sa.Column("net_income", sa.Numeric(20, 2), nullable=True),
        sa.Column("basic_eps", sa.Numeric(18, 4), nullable=True),
        sa.Column("diluted_eps", sa.Numeric(18, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_stock_finq_symbol", "stock_financials_quarterly", ["symbol"], unique=False)
    op.create_index(
        "idx_stock_finq_year_quarter",
        "stock_financials_quarterly",
        ["fiscal_year", "fiscal_quarter"],
        unique=False,
    )
    op.create_index(
        "uq_stock_finq_symbol_year_quarter",
        "stock_financials_quarterly",
        ["symbol", "fiscal_year", "fiscal_quarter"],
        unique=True,
    )

    # stock_holders_institutional
    op.create_table(
        "stock_holders_institutional",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("holder_name", sa.String(length=200), nullable=True),
        sa.Column("shares", sa.Integer(), nullable=True),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.Column("pct_held", sa.Numeric(6, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "idx_institutional_symbol", "stock_holders_institutional", ["symbol"], unique=False
    )
    op.create_index(
        "idx_institutional_asof", "stock_holders_institutional", ["as_of_date"], unique=False
    )
    op.create_index(
        "idx_institutional_holder", "stock_holders_institutional", ["holder_name"], unique=False
    )
    op.create_index(
        "uq_institutional_symbol_asof_holder",
        "stock_holders_institutional",
        ["symbol", "as_of_date", "holder_name"],
        unique=True,
    )

    # stock_holders_mutualfund
    op.create_table(
        "stock_holders_mutualfund",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("fund_name", sa.String(length=200), nullable=False),
        sa.Column("fund_type", sa.String(length=50), nullable=True),
        sa.Column("fund_shares", sa.Numeric(20, 0), nullable=True),
        sa.Column("fund_percent", sa.Numeric(6, 4), nullable=True),
        sa.Column("reported_shares", sa.Numeric(20, 0), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("filing_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_mutualfund_symbol", "stock_holders_mutualfund", ["symbol"], unique=False)
    op.create_index("idx_mutualfund_asof", "stock_holders_mutualfund", ["as_of_date"], unique=False)
    op.create_index("idx_mutualfund_fund", "stock_holders_mutualfund", ["fund_name"], unique=False)
    op.create_index(
        "uq_mutualfund_symbol_asof_fund",
        "stock_holders_mutualfund",
        ["symbol", "as_of_date", "fund_name", "source"],
        unique=True,
    )

    # stock_insider_transactions
    op.create_table(
        "stock_insider_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("insider_name", sa.String(length=200), nullable=False),
        sa.Column("relationship", sa.String(length=100), nullable=True),
        sa.Column("transaction_type", sa.String(length=50), nullable=True),
        sa.Column("shares", sa.Numeric(20, 0), nullable=True),
        sa.Column("price", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_value", sa.Numeric(24, 2), nullable=True),
        sa.Column("ownership_after", sa.Numeric(20, 0), nullable=True),
        sa.Column("ownership_percent", sa.Numeric(6, 4), nullable=True),
        sa.Column("filing_url", sa.String(length=500), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_insider_symbol", "stock_insider_transactions", ["symbol"], unique=False)
    op.create_index(
        "idx_insider_date", "stock_insider_transactions", ["transaction_date"], unique=False
    )
    op.create_index(
        "idx_insider_name", "stock_insider_transactions", ["insider_name"], unique=False
    )
    op.create_index(
        "uq_insider_symbol_name_date_type",
        "stock_insider_transactions",
        ["symbol", "insider_name", "transaction_date", "transaction_type"],
        unique=True,
    )

    # stock_shares_outstanding
    op.create_table(
        "stock_shares_outstanding",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("shares_outstanding", sa.Numeric(20, 0), nullable=True),
        sa.Column("fully_diluted_shares", sa.Numeric(20, 0), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_stock_shares_symbol", "stock_shares_outstanding", ["symbol"], unique=False)
    op.create_index(
        "idx_stock_shares_date", "stock_shares_outstanding", ["as_of_date"], unique=False
    )

    # stock_splits
    op.create_table(
        "stock_splits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("split_date", sa.Date(), nullable=False),
        sa.Column("ratio", sa.Numeric(18, 8), nullable=False),
        sa.Column("split_type", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_stock_splits_symbol", "stock_splits", ["symbol"], unique=False)
    op.create_index("idx_stock_splits_date", "stock_splits", ["split_date"], unique=False)

    # stock_basic_info
    op.create_table(
        "stock_basic_info",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False, unique=True),
        sa.Column("short_name", sa.String(length=100), nullable=True),
        sa.Column("long_name", sa.String(length=200), nullable=True),
        sa.Column("sector", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=50), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("website", sa.String(length=200), nullable=True),
        sa.Column("full_time_employees", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_stock_basic_sector", "stock_basic_info", ["sector"], unique=False)
    op.create_index("idx_stock_basic_industry", "stock_basic_info", ["industry"], unique=False)

    # stock_cashflow_annual
    op.create_table(
        "stock_cashflow_annual",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("operating_cashflow", sa.Numeric(20, 2), nullable=True),
        sa.Column("investing_cashflow", sa.Numeric(20, 2), nullable=True),
        sa.Column("financing_cashflow", sa.Numeric(20, 2), nullable=True),
        sa.Column("net_change_in_cash", sa.Numeric(20, 2), nullable=True),
        sa.Column("free_cashflow", sa.Numeric(20, 2), nullable=True),
        sa.Column("cash_and_equivalents_end", sa.Numeric(20, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_stock_cashflow_symbol", "stock_cashflow_annual", ["symbol"], unique=False)
    op.create_index(
        "idx_stock_cashflow_year", "stock_cashflow_annual", ["fiscal_year"], unique=False
    )

    # stock_cashflow_quarterly
    op.create_table(
        "stock_cashflow_quarterly",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("fiscal_quarter", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("operating_cashflow", sa.Numeric(20, 2), nullable=True),
        sa.Column("investing_cashflow", sa.Numeric(20, 2), nullable=True),
        sa.Column("financing_cashflow", sa.Numeric(20, 2), nullable=True),
        sa.Column("free_cashflow", sa.Numeric(20, 2), nullable=True),
        sa.Column("capital_expenditure", sa.Numeric(20, 2), nullable=True),
        sa.Column("additional_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "idx_stock_cashflowq_symbol", "stock_cashflow_quarterly", ["symbol"], unique=False
    )
    op.create_index(
        "idx_stock_cashflowq_year_quarter",
        "stock_cashflow_quarterly",
        ["fiscal_year", "fiscal_quarter"],
        unique=False,
    )
    op.create_index(
        "uq_stock_cashflowq_symbol_year_quarter",
        "stock_cashflow_quarterly",
        ["symbol", "fiscal_year", "fiscal_quarter"],
        unique=True,
    )
