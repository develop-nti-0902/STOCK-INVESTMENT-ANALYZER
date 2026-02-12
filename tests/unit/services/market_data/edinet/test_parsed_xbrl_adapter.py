"""Unit tests for parsed_xbrl_adapter helpers.

These tests verify `get_data` and `extract_first_numeric` behaviors with
simple adapter-like objects.
"""

from app.services.market_data.edinet.common.parsed_xbrl_adapter import (
    extract_first_numeric,
    get_data,
)


class OneArgParsed:
    """Adapter-like object that exposes single-argument get_data_by_context_ref.

    Args:
        value: value to return from `get_data_by_context_ref`.
    """

    def __init__(self, value):
        """Initialize with stored value."""
        self._value = value

    def get_data_by_context_ref(self, arg):
        """Return the stored value ignoring context."""
        return self._value


class TwoArgParsed:
    """Adapter-like object that exposes two-argument get_data_by_context_ref.

    Args:
        mapping: dict mapping (tag, ctx) -> value
    """

    def __init__(self, mapping):
        """Initialize with mapping."""
        self._mapping = mapping

    def get_data_by_context_ref(self, tag, ctx):
        """Return mapping value for the (tag, ctx) pair."""
        return self._mapping.get((tag, ctx))


def test_get_data_one_arg():
    """get_data should return the underlying list for one-arg adapters."""
    p = OneArgParsed([1, 2, 3])
    assert get_data(p, ctx="ctx") == [1, 2, 3]


def test_get_data_two_arg():
    """get_data should return mapped value for two-arg adapters."""
    p = TwoArgParsed({("t", "c"): 5})
    assert get_data(p, tag="t", ctx="c") == 5


def test_extract_first_numeric():
    """extract_first_numeric should return first numeric string converted."""
    p = TwoArgParsed({("a", "c1"): "100", ("b", "c2"): "200"})
    val = extract_first_numeric(p, tags=["a", "b"], contexts=["c1", "c2"])
    assert float(val) == 100.0
