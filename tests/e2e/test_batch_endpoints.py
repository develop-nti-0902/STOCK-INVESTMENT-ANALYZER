import pytest


@pytest.mark.asyncio
async def test_run_jpx_all_multi_sequence_success(client, mock_db_session):
    """JPXバッチ連続実行APIのテスト - 正常系."""
    payload = {"batch_size": 50}
    response = client.post(
        "/api/v1/batch/stock-data/jpx-all/multi/run_sequence", json=payload
    )

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert data["overall_status"] == "PENDING"
    assert "results" in data


@pytest.mark.asyncio
async def test_run_jpx_all_multi_sequence_with_custom_batch_size(
    client, mock_db_session
):
    """JPXバッチ連続実行API - カスタムバッチサイズでのテスト."""
    payload = {"batch_size": 100}
    response = client.post(
        "/api/v1/batch/stock-data/jpx-all/multi/run_sequence", json=payload
    )

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data


@pytest.mark.asyncio
async def test_run_jpx_all_multi_sequence_default_batch_size(
    client, mock_db_session
):
    """JPXバッチ連続実行API - デフォルトバッチサイズでのテスト."""
    payload = {}
    response = client.post(
        "/api/v1/batch/stock-data/jpx-all/multi/run_sequence", json=payload
    )

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data


@pytest.mark.asyncio
async def test_run_jpx_all_multi_sequence_invalid_batch_size(
    client, mock_db_session
):
    """JPXバッチ連続実行API - 無効なバッチサイズでのバリデーションテスト."""
    payload = {"batch_size": 0}
    response = client.post(
        "/api/v1/batch/stock-data/jpx-all/multi/run_sequence", json=payload
    )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_run_jpx_all_multi_sequence_batch_size_too_large(
    client, mock_db_session
):
    """JPXバッチ連続実行API - バッチサイズ上限超過のバリデーションテスト."""
    payload = {"batch_size": 300}
    response = client.post(
        "/api/v1/batch/stock-data/jpx-all/multi/run_sequence", json=payload
    )

    assert response.status_code in [400, 422]
