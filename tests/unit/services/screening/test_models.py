# -*- coding: utf-8 -*-
"""Test screening models."""


def test_import():
    """Test that the module can be imported."""
    from app.services.screening.models import ScreeningConfig, ScreeningResult

    assert ScreeningConfig is not None
    assert ScreeningResult is not None
