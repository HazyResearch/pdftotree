"""Test table area detection."""
from bs4 import BeautifulSoup

import pdftotree
from pdftotree.core import load_model
from pdftotree.visual.visual_utils import predict_heatmap


def test_vision_model():
    """Check if the vision model runs and returns results in expected format."""
    pdf_file = "tests/input/paleo.pdf"
    model_path = "tests/input/paleo_visual_model.h5"
    model = load_model("vision", model_path)
    page_num = 0
    image, pred = predict_heatmap(
        pdf_file, page_num, model
    )  # index start at 0 with wand
    assert image.shape == (448, 448, 3)
    assert pred.shape == (448, 448)


# TODO: add test_ml_model and test_heuristic_model


def test_cell_values_not_missing():
    output = pdftotree.parse("tests/input/md.pdf")
    soup = BeautifulSoup(output, "lxml")
    table = soup.find(class_="ocr_table")
    assert list(table.find_all("tr")[3].stripped_strings) == [
        "Erin",
        "lamb",
        "madras",
        "HOT",
        "$5",
    ]
