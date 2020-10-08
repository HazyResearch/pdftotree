#!/usr/bin/env python
import os
from subprocess import PIPE, Popen
from typing import Optional

from bs4 import BeautifulSoup
from bs4.element import Tag
from shapely.geometry import box

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
    output = pdftotree.parse("tests/input/CaseStudy_ACS.pdf")
    soup = BeautifulSoup(output, "lxml")
    assert len(soup.find_all(class_="ocrx_word")) >= 1000
    assert len(soup.find_all("figure")) == 3

    # Adapted from https://github.com/ocropus/hocr-tools/blob/v1.3.0/hocr-check
    def get_prop(node: Tag, name: str) -> Optional[str]:
        title = node.get("title")
        if not title:
            return None
        props = title.split(";")
        for prop in props:
            (key, args) = prop.split(None, 1)
            if key == name:
                return args
        return None

    # Adapted from https://github.com/ocropus/hocr-tools/blob/v1.3.0/hocr-check
    def get_bbox(node: Tag) -> box:
        bbox = get_prop(node, "bbox")
        if not bbox:
            return None
        return box(*[int(x) for x in bbox.split()])

    # Check if words are extracted even though they are overlapped by a figure (#77).
    page = soup.find(class_="ocr_page")  # checking only 1st page is good enough.
    words = [get_bbox(word) for word in page.find_all(class_="ocrx_word")]
    figure = get_bbox(page.find("figure"))
    assert all([figure.contains(word) for word in words])


def test_LTChar_under_LTFigure():
    """Test on a PDF where LTChar(s) are children of LTFigure."""
    output = pdftotree.parse("tests/input/CentralSemiconductorCorp_2N4013.pdf")
    soup = BeautifulSoup(output, "lxml")
    line: Tag = soup.find(class_="ocrx_line")
    assert [word.text for word in line.find_all(class_="ocrx_word")] == [
        "Small",
        "Signal",
        "Transistors",
    ]

    # The table in the 1st page should contain 18 columns
    page = soup.find(class_="ocr_page")
    table = page.find("table")
    assert len(table.find("tr").find_all("td")) == 18


def test_ml_completion():
    """Simply test that ML-based parse runs without errors."""
    output = pdftotree.parse(
        "tests/input/paleo.pdf",
        model_type="ml",
        model_path="tests/input/paleo_model.pkl",
    )
    assert output is not None


def test_vision_completion():
    """Simply test that vision-based parse runs without errors."""
    output = pdftotree.parse(
        "tests/input/paleo.pdf",
        model_type="vision",
        model_path="tests/input/paleo_visual_model.h5",
    )
    assert output is not None
