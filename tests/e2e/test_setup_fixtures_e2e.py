"""Setup and fixture verification E2E tests.

マスタデータ投入と基本的なセットアップが正常に動作することを確認するテスト。
"""

# flake8: noqa

import pytest

from tests.e2e.utils import (
    assert_artifact_written,
    cleanup_table,
    fetch_stock_master_for_artifact,
    run_async_safely,
    verify_stock_master_has_data,
    write_csv_artifact,
)

# Ensure all e2e tests run on the same xdist worker (loadgroup)
pytestmark = pytest.mark.xdist_group("e2e")


def test_setup_stock_master_is_ready(client):
    """Setup: stock_master の基本セットアップが正常に動作することを確認.

    手順:
    1. stock_master テーブルをクリーンアップ
    2. /api/v1/stock-master/fetch/sample でサンプルマスタを投入
    3. DB に格納されたことを確認（存在確認のみ）
    4. artifact を出力（デバッグ支援）
    """
    from app.models.market_data.stock_master import StockMaster

    # 事前クリーンアップ
    cleanup_table(StockMaster)

    # 1. sample を投入（sample_size=10, batch_size=10）
    sample_url = "/api/v1/stock-master/fetch/sample?sample_size=10&batch_size=10"
    r_sample = client.post(sample_url)
    assert r_sample.status_code in (
        200,
        201,
        204,
    ), f"Unexpected status code: {r_sample.status_code}"

    # 2. DB に格納されたことを確認（存在確認のみ）
    has_data = verify_stock_master_has_data()
    assert has_data, "Setup failed: stock_master テーブルに格納されたデータが見つかりません"
