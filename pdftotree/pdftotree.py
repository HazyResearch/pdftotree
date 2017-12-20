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

import argparse
import os
import pickle
import sys
import codecs
import re

import numpy as np
from ml.TableExtractML import TableExtractorML
from TreeExtract import TreeExtractor
from TreeVisualizer import TreeVisualizer

def load_model(model_path):
    print("Loading pretrained model for table detection")
    model = pickle.load(open(model_path, 'rb'))
    print("Model loaded!")
    return model

def visualize_tree(pdf_file, pdf_tree, html_path):
    v = TreeVisualizer(pdf_file)
    filename_prefix = os.path.basename(pdf_file)
    a = v.display_candidates(pdf_tree, html_path, filename_prefix)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="""Script to extract tree structure from PDF files.""")
    parser.add_argument('--model_path', type=str, default=None, help='pretrained model')
    parser.add_argument('--pdf_file', type=str, help='pdf file name for which tree structure needs to be extracted')
    parser.add_argument('--html_path', type=str, help='path where tree structure must be saved', default="./results/")
    parser.add_argument('--favor_figures', type=str, help='whether figures must be favored over other parts such as tables and section headers', default="True")
    parser.add_argument('--visualize', dest="visualize", action="store_true", help='whether to output visualization images for the tree')
    parser.set_defaults(visualize=False)
    args = parser.parse_args()
    model = None
    if (args.model_path is not None):
        model = load_model(args.model_path)
    extractor = TreeExtractor(args.pdf_file)
    if(not extractor.is_scanned()):
        print("Digitized PDF detected, building tree structure")
        pdf_tree = extractor.get_tree_structure(model, args.favor_figures)
        print("Tree structure built, creating html")
        pdf_html = extractor.get_html_tree()
        print("HTML created, writing to file")
        pdf_filename = os.path.basename(args.pdf_file)
        # Check html_path exists, create if not
        if not os.path.exists(args.html_path):
            os.makedirs(args.html_path)
        reload(sys)
        sys.setdefaultencoding('utf8')
        pdf_html = re.sub(r'[\x00-\x1F]+', '', pdf_html)
        with codecs.open(args.html_path + pdf_filename[:-4] + ".html", encoding="utf-8", mode="w") as f:
            f.write(pdf_html.encode("utf-8"))
        if args.visualize:
            imgs = visualize_tree(args.pdf_file, pdf_tree, args.html_path)
    else:
        print("Document is scanned, cannot build tree structure")
