import pytest

from app.services.market_data.edinet.common import parsed_xbrl_adapter as adapter


class PXTwoArg:
    def get_data_by_context_ref(self, tag, ctx):
        return f"{tag}:{ctx}"


class PXOneArgPrefersCtx:
    def get_data_by_context_ref(self, *args):
        # Simulate implementation that raises TypeError for two-arg calls
        if len(args) == 2:
            raise TypeError("wrong arg count")
        return args[0]


class PXFallbacks:
    def get(self, key):
        return f"got:{key}"


class PXNumeric:
    def __init__(self, mapping):
        self.mapping = mapping

    def get_data_by_context_ref(self, *args):
        # support both (tag, ctx) and (single)
        if len(args) == 2:
            return self.mapping.get((args[0], args[1]))
        return self.mapping.get(args[0])


def test_get_data_with_two_arg_signature():
    px = PXTwoArg()
    res = adapter.get_data(px, tag="TAG", ctx="CTX")
    assert res == "TAG:CTX"


def test_get_data_falls_back_to_single_ctx_when_two_arg_raises_typeerror():
    px = PXOneArgPrefersCtx()
    # when both provided, two-arg call raises TypeError, then ctx-only is attempted
    res = adapter.get_data(px, tag="IGNORED", ctx="CTX")
    assert res == "CTX"


def test_get_data_uses_fallback_getter_names():
    px = PXFallbacks()
    res = adapter.get_data(px, tag="T")
    assert res == "got:T"


def test_extract_first_numeric_prefers_first_matching_tag_context():
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
    mapping = {
        ("tA", "cX"): None,
        ("tB", "cX"): ["100"],
        ("tC", "cX"): {"k": "200"},
    }
    px = PXNumeric(mapping)

    # First numeric comes from tB -> list[0]
    val = adapter.extract_first_numeric(px, tags=["tA", "tB", "tC"], contexts=["cX"])
    assert val == pytest.approx(100.0)


def test_extract_first_numeric_returns_none_when_no_numeric_found():
    mapping = {("tx", "cx"): "not-a-number", ("ty", "cx"): [], ("tz", "cx"): {}}
    px = PXNumeric(mapping)

    val = adapter.extract_first_numeric(px, tags=["tx", "ty", "tz"], contexts=["cx"])
    assert val is None
