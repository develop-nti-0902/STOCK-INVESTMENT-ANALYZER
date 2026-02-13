"""Tests for parsed_xbrl_adapter utilities handling different provider APIs."""

import pytest

from app.services.market_data.edinet.common import parsed_xbrl_adapter as adapter


class PXTwoArg:
    """Provider exposing two-argument get_data_by_context_ref(tag, ctx)."""

    def get_data_by_context_ref(self, tag, ctx):
        """Return a simple string combining tag and context for tests."""
        return f"{tag}:{ctx}"


class PXOneArgPrefersCtx:
    """Provider that prefers single-arg call and raises on two-arg invocation."""

    def get_data_by_context_ref(self, *args):
        """Emulate provider that accepts single-arg and errors on two-args."""
        if len(args) == 2:
            raise TypeError("wrong arg count")
        return args[0]


class PXFallbacks:
    """Provider exposing fallback getter `get(key)`."""

    def get(self, key):
        """Return a fallback value for the given key for tests."""
        return f"got:{key}"


class PXNumeric:
    """Provider returning numeric values from mapping supporting different signatures."""

    def __init__(self, mapping):
        """Store mapping used to emulate provider values."""
        self.mapping = mapping

    def get_data_by_context_ref(self, *args):
        """Support both (tag, ctx) and single-arg signatures."""
        if len(args) == 2:
            return self.mapping.get((args[0], args[1]))
        return self.mapping.get(args[0])


def test_get_data_with_two_arg_signature():
    """Use two-argument provider signature when available."""
    px = PXTwoArg()
    res = adapter.get_data(px, tag="TAG", ctx="CTX")
    assert res == "TAG:CTX"


def test_get_data_falls_back_to_single_ctx_when_two_arg_raises_typeerror():
    """Fallback to single-arg context accessor when two-arg call raises TypeError."""
    px = PXOneArgPrefersCtx()
    res = adapter.get_data(px, tag="IGNORED", ctx="CTX")
    assert res == "CTX"


def test_get_data_uses_fallback_getter_names():
    """Try common fallback getter names when primary accessor missing."""
    px = PXFallbacks()
    res = adapter.get_data(px, tag="T")
    assert res == "got:T"


def test_extract_first_numeric_prefers_first_matching_tag_context():
    """Extract first numeric value matching tags and contexts ordering."""
    mapping = {
        ("t1", "c1"): "12.3",
        ("t2", "c1"): ["45.6"],
        ("t3", "c1"): {"a": "78.9"},
    }
    px = PXNumeric(mapping)

    val = adapter.extract_first_numeric(px, tags=["not", "t1", "t2"], contexts=["c1"])
    assert isinstance(val, float)
    assert val == pytest.approx(12.3)


def test_extract_first_numeric_handles_list_and_dict_values():
    """Handle list and dict typed values when extracting numeric."""
    mapping = {
        ("tA", "cX"): None,
        ("tB", "cX"): ["100"],
        ("tC", "cX"): {"k": "200"},
    }
    px = PXNumeric(mapping)

    val = adapter.extract_first_numeric(px, tags=["tA", "tB", "tC"], contexts=["cX"])
    assert val == pytest.approx(100.0)


def test_extract_first_numeric_returns_none_when_no_numeric_found():
    """Return None when no numeric values are present for tags/contexts."""
    mapping = {("tx", "cx"): "not-a-number", ("ty", "cx"): [], ("tz", "cx"): {}}
    px = PXNumeric(mapping)

    val = adapter.extract_first_numeric(px, tags=["tx", "ty", "tz"], contexts=["cx"])
    assert val is None
