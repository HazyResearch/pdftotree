# Tree Structure - Table Extraction

Fonduer has been successfully extended to perform information extraction from richly formatted data such as tables. A crucial step in this process is the construction of the hierarchical tree of context objects such as text blocks, figures, tables, etc. The system currently uses PDF to HTML conversion provided by Adobe Acrobat converter. Adobe Acrobat converter is not an open source tool and this can be very inconvenient for Fonduer users. We therefore need to build our own module as replacement to Adobe Acrobat. Several open source tools are available for pdf to html conversion but these tools do not preserve the cell structure in a table. Our goal in this project is to develop a tool that extracts text, figures and tables in a pdf document and maintains the structure of the document using a tree data structure. 

This project is using the table-extraction tool (https://github.com/xiao-cheng/table-extraction). 

## Dependencies 

```pip install -r requirements.txt```

```./install-poppler.sh```

## Environment variables 

First, set environment variables. The ```DATAPATH``` folder should contain the pdf files that need to be processed. 

```source set_env.sh```

## Tutorial
 
The ```table-extraction/tutorials/``` folder contains a notebook ```table-extraction-demo.ipynb```. In this demo we detail the different steps of the table extraction tool and display some examples of table detection results for paleo papers. However, to extract tables for new documents, the user should directly use the command line tool detailed in the next section. 

## Command Line Usage

To use the tool via command line, run:

```source set_env.sh```

```python table-extraction/ml/extract_tables.py [-h]```

```
usage: extract_tables.py [-h] [--mode MODE] [--train-pdf TRAIN_PDF]
                         [--test-pdf TEST_PDF] [--gt-train GT_TRAIN]
                         [--gt-test GT_TEST] [--model-path MODEL_PATH]
                         [--iou-thresh IOU_THRESH]

Script to extract tables bounding boxes from PDF files using a machine
learning approach. if model.pkl is saved in the model-path, the pickled model
will be used for prediction. Otherwise the model will be retrained. If --mode
is test (by default), the script will create a .bbox file containing the
tables for the pdf documents listed in the file --test-pdf. If --mode is dev,
the script will also extract ground truth labels fot the test data and compute
some statistics. To run the script on new documents, specify the path to the
list of pdf to analyze using the argument --test-pdf. Those files must be
saved in the DATAPATH folder.

optional arguments:
  -h, --help            show this help message and exit
  --mode MODE           usage mode dev or test, default is test
  --train-pdf TRAIN_PDF
                        list of pdf file names used for training. Those files
                        must be saved in the DATAPATH folder (cf set_env.sh)
                        must be saved in the DATAPATH folder (cf set_env.sh)
  --test-pdf TEST_PDF   list of pdf file names used for testing. Those files
                        must be saved in the DATAPATH folder (cf set_env.sh)
  --gt-train GT_TRAIN   ground truth train tables
  --gt-test GT_TEST     ground truth test tables
  --model-path MODEL_PATH
                        pretrained model
  --iou-thresh IOU_THRESH
                        intersection over union threshold to remove duplicate
                        tables
```
                        
                        
Each document must be saved in the ```DATAPATH``` folder. 

The script will create a ``` .bbox``` file where each row contains tables coordinates of the corresponding row document in the --test_pdf file.

The bounding boxes are stored in the format (page_num, page_width, page_height, top, left, bottom, right) and are separated with ";". 

## Evaluation

We provide an evaluation code to compute recall, precision and F1 score at the character level. 

```python table-extraction/evaluation/char_level_evaluation.py [-h] pdf_files extracted_bbox gt_bbox```

```
usage: char_level_evaluation.py [-h] pdf_files extracted_bbox gt_bbox

Computes scores for the table localization task. Returns Recall and Precision
for the sub-objects level (characters in text). If DISPLAY=TRUE, display GT in
Red and extracted bboxes in Blue

positional arguments:
  pdf_files       list of paths of PDF file to process
  extracted_bbox  extracting bounding boxes (one line per pdf file)
  gt_bbox         ground truth bounding boxes (one line per pdf file)

optional arguments:
  -h, --help      show this help message and exit
```
