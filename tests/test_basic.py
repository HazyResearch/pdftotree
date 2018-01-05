#!/usr/bin/env python
import pytest
import six
from tests.context import pdftotree


def test_heuristic_completion():
    """Simply test that parse runs to completion without errors."""
    output = pdftotree.parse("tests/input/paleo.pdf", "tests/output/",
                             debug=True)

    assert output is not None


def test_ml_completion():
    """Simply test that ML-based parse runs without errors."""
    if six.PY2:
        pdftotree.parse("tests/input/paleo.pdf", "tests/output/",
                        model_path="tests/input/paleo_model.pkl")
    else:
        pytest.skip("Don't have a Python3 compatible model for testing.")
