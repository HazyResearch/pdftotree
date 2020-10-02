#!/usr/bin/env python
import os
from subprocess import PIPE, Popen

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


def test_output_should_conform_to_hocr(tmp_path):
    """Test if an exported file conform to hOCR."""
    html_path = os.path.join(tmp_path, "md.html")
    pdftotree.parse("tests/input/md.pdf", html_path)
    with Popen(["hocr-check", html_path], stderr=PIPE) as proc:
        assert all([line.decode("utf-8").startswith("ok") for line in proc.stderr])


def test_visualize_output(tmp_path):
    """Test if an output can be visualzied."""
    html_path = os.path.join(tmp_path, "md.html")
    pdftotree.parse("tests/input/md.pdf", html_path, visualize=True)


def test_looks_scanned():
    """Test on a PDF that looks like a scanned one but not.

    CaseStudy_ACS.pdf contains a transparent image overlaying the entire page.
    This overlaying transparent image fools TreeExtractor into thinking it is scanned.
    """
    output = pdftotree.parse("tests/input/CaseStudy_ACS.pdf", favor_figures="True")
    assert output.count("ocrx_word") == 1  # single appearance in ocr-capabilities
    output = pdftotree.parse("tests/input/CaseStudy_ACS.pdf", favor_figures="False")
    assert output.count("ocrx_word") >= 1000


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
