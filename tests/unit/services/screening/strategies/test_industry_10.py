# -*- coding: utf-8 -*-
"""Test Industry10 strategy."""


def test_import():
    """Test that the module can be imported."""
    import importlib

    mod = importlib.import_module("app.services.screening.strategies.industry_10")
    assert mod is not None
