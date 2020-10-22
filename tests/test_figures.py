"""Test figures."""
from bs4 import BeautifulSoup

import pdftotree


def test_figures():
    output = pdftotree.parse("tests/input/md.pdf")
    soup = BeautifulSoup(output, "lxml")
    imgs = soup.find_all("img")
    assert len(imgs) == 1
