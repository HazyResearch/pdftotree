"""
This script takes a PDF document and extracts it's tree structure and then
writes the HTML based on that tree structure. The components of the tree
structure are:
- Tables
- Table Captions
- Figures
- Figure Captions
- Section Headers
- Paragraphs
- List (References in research papers)
- Page Headers

Tables are detected using a Machine learning model, provide the path in
model_path argument = TreeStructure/data/paleo/ml/model.pkl.

Other tree parts are detected using heuristic methods.
"""
import codecs
import logging
import os
import pickle

from pdftotree.TreeExtract import TreeExtractor
from pdftotree.TreeVisualizer import TreeVisualizer

logger = logging.getLogger(__name__)


def load_model(model_type, model_path):
    logger.info("Loading pretrained {} model for table detection".format(model_type))
    if model_type == "ml":
        model = pickle.load(open(model_path, "rb"))
    else:
        from keras.models import load_model as load_vision_model

        model = load_vision_model(model_path)
    logger.info("Model loaded!")
    return model


def visualize_tree(pdf_file, pdf_tree, html_path):
    v = TreeVisualizer(pdf_file)
    filename_prefix = os.path.basename(pdf_file)
    v.display_candidates(pdf_tree, html_path, filename_prefix)


def parse(
    pdf_file,
    html_path=None,
    model_type=None,
    model_path=None,
    visualize=False,
):
    model = None
    if model_type is not None and model_path is not None:
        model = load_model(model_type, model_path)
    extractor = TreeExtractor(pdf_file)
    if extractor.is_scanned():
        logger.warning("Document looks scanned, the result may be far from expected.")
    else:
        logger.info("Digitized PDF detected, building tree structure...")

    pdf_tree = extractor.get_tree_structure(model_type, model)
    logger.info("Tree structure built, creating html...")
    pdf_html = extractor.get_html_tree()
    logger.info("HTML created.")
    # TODO: what is the following substition for and is it required?
    # pdf_html = re.sub(r"[\x00-\x1F]+", "", pdf_html)

    if html_path is None:
        return pdf_html
    with codecs.open(html_path, encoding="utf-8", mode="w") as f:
        f.write(pdf_html)
    if visualize:
        visualize_tree(pdf_file, pdf_tree, html_path)
