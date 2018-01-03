#!/usr/bin/env python
from tests.context import pdftotree

def test_completion():
    """Simply test that parse runs to completion without errors."""
    output = pdftotree.parse("tests/input/112823.pdf", "tests/output/", debug=True)

    assert output is not None


