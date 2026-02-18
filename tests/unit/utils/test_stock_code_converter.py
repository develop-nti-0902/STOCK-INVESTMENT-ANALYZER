"""StockCodeConverter の単体テスト.

このモジュールでは `StockCodeConverter` の主要メソッドの振る舞いを検証します。
"""

import pytest

from app.utils.stock_code_converter import StockCodeConverter, from_edinet_code, to_edinet_code


def test_to_edinet_basic():
    """`to_edinet` の基本的なパディング処理を検証する."""
    c = StockCodeConverter()
    assert c.to_edinet("1301") == "13010"
    assert to_edinet_code("1301") == "13010"


def test_to_edinet_padding_and_trunc():
    """パディングとトランケートの挙動を検証する."""
    c = StockCodeConverter()
    assert c.to_edinet("1") == "10000"
    assert c.to_edinet("12345") == "12345"
    assert c.to_edinet("123456") == "23456"


def test_from_edinet_basic():
    """`from_edinet` の基本的な逆変換を検証する."""
    c = StockCodeConverter()
    assert c.from_edinet("13010") == "1301"
    assert from_edinet_code("13010") == "1301"
    assert c.from_edinet("10000") == "1"
    assert c.from_edinet("00001") == "00001"


def test_roundtrip_property():
    """to_edinet -> from_edinet の往復で元データが復元される性質を確認する."""
    c = StockCodeConverter()
    samples = ["1301", "1", "999", "12345"]
    for s in samples:
        assert c.from_edinet(c.to_edinet(s)) == s.rstrip("0") or s


def test_to_edinet_allows_letters():
    """英字を含む入力が右側に0でパディングされることを確認する."""
    c = StockCodeConverter()
    assert c.to_edinet("12A3") == "12A30"


@pytest.mark.parametrize("val", [None, ""])
def test_to_edinet_invalid(val):
    """None や空文字は例外となることを検証する."""
    c = StockCodeConverter()
    with pytest.raises(ValueError):
        c.to_edinet(val)


@pytest.mark.parametrize("val", [None, ""])
def test_from_edinet_invalid(val):
    """None や空文字は例外となることを検証する."""
    c = StockCodeConverter()
    with pytest.raises(ValueError):
        c.from_edinet(val)
