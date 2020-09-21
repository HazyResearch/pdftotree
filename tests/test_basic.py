#!/usr/bin/env python
import os

import pdftotree


def test_heuristic_completion():
    """Simply test that parse runs to completion without errors."""
    output = pdftotree.parse("tests/input/paleo.pdf")
    assert output is not None


def test_cli_should_output_at_given_path(tmp_path):
    """Test if CLI produces an HTML at a given path."""
    html_path = os.path.join(tmp_path, "paleo.html")
    pdftotree.parse("tests/input/paleo.pdf", html_path)
    assert os.path.isfile(html_path)


def test_ml_completion():
    """Simply test that ML-based parse runs without errors."""
    output = pdftotree.parse(
        "tests/input/paleo.pdf",
        model_type="ml",
        model_path="tests/input/paleo_model.pkl",
    )
    assert output is not None


def test_visual_completion():
    """Simply test that ML-based parse runs without errors."""
    output = pdftotree.parse(
        "tests/input/paleo.pdf",
        model_type="visual",
        model_path="tests/input/paleo_visual_model.h5",
    )
    assert output is not None
