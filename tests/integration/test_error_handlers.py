from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.exceptions import AppException
from app.main import app as fastapi_app


@fastapi_app.get("/__test_raise_app_exc")
async def _raise_app_exc():
    raise AppException(message="boom", error_code="BOOM_ERR", status_code=418)


@fastapi_app.get("/__test_raise_http_dict")
async def _raise_http_dict():
    raise HTTPException(
        status_code=400,
        detail={"error": "HTTP_BAD", "message": "bad", "details": {"x": 1}},
    )


@fastapi_app.get("/__test_raise_http_str")
async def _raise_http_str():
    raise HTTPException(status_code=404, detail="not found")


@fastapi_app.get("/__test_validate")
async def _validate(x: int):
    return {"x": x}


@fastapi_app.get("/__test_raise_general")
async def _raise_general():
    raise Exception("oops")


def test_app_exception_handler_via_testclient():
    with TestClient(fastapi_app) as client:
        resp = client.get("/__test_raise_app_exc")
        assert resp.status_code == 418
        body = resp.json()
        assert body["error"]["code"] == "BOOM_ERR"
        assert body["error"]["message"] == "boom"
        assert "request_id" in body["meta"]


def test_http_exception_handler_with_dict_detail():
    with TestClient(fastapi_app) as client:
        resp = client.get("/__test_raise_http_dict")
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "HTTP_BAD"
        assert body["error"]["message"] == "bad"
        assert body["error"]["details"] == {"x": 1}


def test_http_exception_handler_with_string_detail():
    with TestClient(fastapi_app) as client:
        resp = client.get("/__test_raise_http_str")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "HTTP_ERROR"
        assert body["error"]["message"] == "not found"


def test_validation_exception_handler_for_query_param():
    # 非整数を渡してバリデーションエラーを発生させる
    with TestClient(fastapi_app) as client:
        resp = client.get("/__test_validate?x=abc")
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "validation_errors" in body["error"]["details"]
        # フィールド情報に x が含まれていること
        validation_errors = body["error"]["details"]["validation_errors"]
        fields = [e.get("field", "") for e in validation_errors]
        assert any("x" in f for f in fields)


def test_general_exception_handler_hides_traceback_when_not_debug():
    # DEBUG=False のときは詳細なトレースバックを返さない
    original = getattr(fastapi_app.state.settings, "DEBUG", None)
    fastapi_app.state.settings.DEBUG = False
    try:
        with TestClient(fastapi_app, raise_server_exceptions=False) as client:
            resp = client.get("/__test_raise_general")
            assert resp.status_code == 500
            body = resp.json()
            assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
            assert "An unexpected error occurred" in body["error"]["message"]
            assert (
                body["error"]["details"].get("exception_type") == "Exception"
            )
            assert "traceback" not in body["error"]["details"]
    finally:
        # restore original DEBUG to avoid side effects for other tests
        if original is None:
            delattr(fastapi_app.state.settings, "DEBUG")
        else:
            fastapi_app.state.settings.DEBUG = original


def test_general_exception_handler_includes_traceback_when_debug():
    # DEBUG=True のときはトレースバックを含める
    original = getattr(fastapi_app.state.settings, "DEBUG", None)
    fastapi_app.state.settings.DEBUG = True
    try:
        with TestClient(fastapi_app, raise_server_exceptions=False) as client:
            resp = client.get("/__test_raise_general")
            assert resp.status_code == 500
            body = resp.json()
            assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
            assert (
                body["error"]["details"].get("exception_type") == "Exception"
            )
            assert "traceback" in body["error"]["details"]
    finally:
        if original is None:
            delattr(fastapi_app.state.settings, "DEBUG")
        else:
            fastapi_app.state.settings.DEBUG = original
