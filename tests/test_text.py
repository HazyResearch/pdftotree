"""Test extracted text."""
import re

from bs4 import BeautifulSoup

import pdftotree


def test_text_is_escaped():
    """Test if text is properly escaped."""
    output = pdftotree.parse("tests/input/md.pdf")
    soup = BeautifulSoup(output, "lxml")
    words = soup.find_all(class_="ocrx_word")
    # Use str() instead of .text as the latter gives unescaped text.
    m = re.search(r">(.+?)<", str(words[66]))
    assert m[1] == "'bar';."

    output = pdftotree.parse("tests/input/112823.pdf")
    soup = BeautifulSoup(output, "lxml")
    words = soup.find_all(class_="ocrx_word")
    m = re.search(r">(.+?)<", str(words[152]))
    assert m[1] == "&amp;"
