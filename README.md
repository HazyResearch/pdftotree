# pdftotree
[![Build Status](https://travis-ci.com/HazyResearch/pdftotree.svg?token=T3shSHjcJk8kMbzHEY7Z&branch=master)](https://travis-ci.com/HazyResearch/pdftotree)

Fonduer has been successfully extended to perform information extraction from
richly formatted data such as tables. A crucial step in this process is the
construction of the hierarchical tree of context objects such as text blocks,
figures, tables, etc. The system currently uses PDF to HTML conversion provided
by Adobe Acrobat converter. Adobe Acrobat converter is not an open source tool
and this can be very inconvenient for Fonduer users. We therefore need to build
our own module as replacement to Adobe Acrobat. Several open source tools are
available for pdf to html conversion but these tools do not preserve the cell
structure in a table. Our goal in this project is to develop a tool that
extracts text, figures and tables in a pdf document and maintains the structure
of the document using a tree data structure.

This project is using the table-extraction tool
(https://github.com/xiao-cheng/table-extraction).

## Dependencies

```pip install -r requirements.txt```

## Usage

To use the commandline tool:
```
usage: extract_tree.py [-h] [--model_path MODEL_PATH] --pdf_file PDF_FILE
                       [--html_path HTML_PATH] [--favor_figures FAVOR_FIGURES]
                       [--visualize]

Script to extract tree structure from PDF files.

optional arguments:
  -h, --help            show this help message and exit
  --model_path MODEL_PATH
                        pretrained model
  --pdf_file PDF_FILE   pdf file name for which tree structure needs to be
                        extracted
  --html_path HTML_PATH
                        path where tree structure must be saved
  --favor_figures FAVOR_FIGURES
                        whether figures must be favored over other parts such
                        as tables and section headers
  --visualize           whether to output visualization images for the tree
```

To use it as a package:
```py
import pdftotree

pdftotree.parse(pdf_file, html_path, model_path=None, favor_figures=True, visualize=False):
```
