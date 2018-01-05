'''
This script takes a PDF document and extracts it's tree structure and then writes the HTML based on that tree structure.
The components of the tree structure are:
- Tables
- Table Captions
- Figures
- Figure Captions
- Section Headers
- Paragraphs
- List (References in research papers)
- Page Headers

Tables are detected using a Machine learning model, provide the path in model_path argument = TreeStructure/data/paleo/ml/model.pkl.

Other tree parts are detected using heuristic methods.

Set favor_figures to "False" for Hardware sheets.
'''
import six  # Python 2-3 compatibility
import os
import pickle
import sys
import codecs
import re

#  import importlib

import numpy as np
from pdftotree.ml.TableExtractML import TableExtractorML
from pdftotree.TreeExtract import TreeExtractor
from pdftotree.TreeVisualizer import TreeVisualizer

def load_model(model_path):
    print("Loading pretrained model for table detection")
    if six.PY3:
        model = pickle.load(open(model_path, 'rb'), encoding="bytes")
    else:
        model = pickle.load(open(model_path, 'rb'))
    print("Model loaded!")
    return model

def visualize_tree(pdf_file, pdf_tree, html_path):
    v = TreeVisualizer(pdf_file)
    filename_prefix = os.path.basename(pdf_file)
    a = v.display_candidates(pdf_tree, html_path, filename_prefix)


def parse(pdf_file, html_path, model_path=None, favor_figures=True, visualize=False, debug=False):
    model = None
    if (model_path is not None):
        model = load_model(model_path)
    extractor = TreeExtractor(pdf_file)
    if(not extractor.is_scanned()):
        print("Digitized PDF detected, building tree structure")
        pdf_tree = extractor.get_tree_structure(model, favor_figures)
        print("Tree structure built, creating html")
        pdf_html = extractor.get_html_tree()
        print("HTML created, writing to file")
        pdf_filename = os.path.basename(pdf_file)
        # Check html_path exists, create if not
        if not os.path.exists(html_path):
            os.makedirs(html_path)
        #  importlib.reload(sys)
        #  sys.setdefaultencoding('utf8')
        pdf_html = re.sub(r'[\x00-\x1F]+', '', pdf_html)
        if debug:
            return pdf_html
        with codecs.open(html_path + pdf_filename[:-4] + ".html",
                         encoding="utf-8", mode="w") as f:
            f.write(pdf_html)
        if visualize:
            visualize_tree(pdf_file, pdf_tree, html_path)
    else:
        print("Document is scanned, cannot build tree structure")
