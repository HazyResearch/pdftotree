# pdftotree
[![GitHub issues](https://img.shields.io/github/issues/HazyResearch/pdftotree.svg)](https://github.com/HazyResearch/pdftotree/projects/2)
[![GitHub license](https://img.shields.io/github/license/HazyResearch/pdftotree.svg)](https://github.com/HazyResearch/pdftotree/blob/master/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/HazyResearch/pdftotree.svg)](https://github.com/HazyResearch/pdftotree/stargazers)
[![Build Status](https://travis-ci.org/HazyResearch/pdftotree.svg?branch=master)](https://travis-ci.org/HazyResearch/pdftotree)

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

```
sudo apt-get install python3-tk
```

## Installation

`pip install git+https://github.com/HazyResearch/pdftotree@master`

## Usage

To use the commandline tool:

```
usage: extract_tree [-h] [--model_path MODEL_PATH] --pdf_file PDF_FILE
                    [--html_path HTML_PATH] [--favor_figures FAVOR_FIGURES]
                    [--visualize] [-v] [-vv]

Script to extract tree structure from PDF files.

optional arguments:
  -h, --help            show this help message and exit
  --model_path MODEL_PATH
                        pretrained model
  --pdf_file PDF_FILE   pdf file name for which tree structure needs to be
                        extracted
  --html_path HTML_PATH
                        path where tree structure should be saved. If none,
                        HTML is printed to stdout.
  --favor_figures FAVOR_FIGURES
                        whether figures must be favored over other parts such
                        as tables and section headers
  --visualize           whether to output visualization images for the tree
  -v                    output INFO level logging.
  -vv                   output DEBUG level logging.
```

To use it as a package:

```py
import pdftotree

pdftotree.parse(pdf_file, html_path=None, model_path=None, favor_figures=True, visualize=False):
```

## For Developers

### Tests

Once you've cloned this repository, first make sure you ahve the dependencies installed

```
pip install -r requirements.txt
```

Then you can run our tests

```
pytest tests -rs
```

To test changes in the package, you can also install it locally in your virtualenv by running
```
python setup.py develop
```
