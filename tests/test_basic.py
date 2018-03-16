#!/usr/bin/env python
import pytest
import sys
from tests.context import pdftotree


def test_heuristic_completion():
    """Simply test that parse runs to completion without errors."""
    output = pdftotree.parse("tests/input/paleo.pdf")
    assert output is not None

def test_ml_completion():
    """Simply test that ML-based parse runs without errors."""
    output = pdftotree.parse(
        "tests/input/paleo.pdf", model_type="ml", model_path="tests/input/paleo_model.pkl")
    assert output is not None

def test_visual_completion():
    """Simply test that ML-based parse runs without errors."""
    output = pdftotree.parse(
        "tests/input/paleo.pdf", model_type="visual", model_path="tests/input/paleo_visual_model.h5")
    assert output is not None
