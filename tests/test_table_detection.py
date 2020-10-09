"""Test table area detection."""

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
