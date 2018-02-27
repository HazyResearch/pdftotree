#!/usr/bin/env python
import logging
import pytest
from bs4 import BeautifulSoup
from pdftotree import TreeExtract

log = logging.getLogger(__name__)

def test_word_coordinates():
    """Return word-level coordinates, not character-level coordinates."""
    # Create a TreeExtractor
    pdf = "tests/input/md.pdf"
    extractor = TreeExtract.TreeExtractor(pdf)
    if (not extractor.is_scanned()):
        log.info("Digitized PDF detected, building tree structure...")
        pdf_tree = extractor.get_tree_structure(None, True)
        pdf_html = extractor.get_html_tree()
        soup = BeautifulSoup(pdf_html, 'html.parser')

        # Simple tests on the first paragraph
        assert (soup.paragraph['words'] == "Unordered lists")

    else:
        pytest.fail("{} is not native digital?".format(pdf))
