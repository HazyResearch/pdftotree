"""Test figures."""
from bs4 import BeautifulSoup

import pdftotree


def test_figures():
    output = pdftotree.parse("tests/input/md.pdf")
    soup = BeautifulSoup(output, "lxml")
    imgs = soup.find_all("img")
    assert len(imgs) == 1

    output = pdftotree.parse("tests/input/CaseStudy_ACS.pdf")
    soup = BeautifulSoup(output, "lxml")
    imgs = soup.find_all("img")
    # 3 jpg, 2 bmp, 5 total images
    assert len(imgs) == 5
    assert len([img for img in imgs if img["src"].startswith("data:image/jpeg")]) == 3
    assert len([img for img in imgs if img["src"].startswith("data:image/bmp")]) == 2
