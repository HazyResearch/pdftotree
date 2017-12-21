# pdftotree

Fonduer has been successfully extended to perform information extraction from richly formatted data such as tables. A crucial step in this process is the construction of the hierarchical tree of context objects such as text blocks, figures, tables, etc. The system currently uses PDF to HTML conversion provided by Adobe Acrobat converter. Adobe Acrobat converter is not an open source tool and this can be very inconvenient for Fonduer users. We therefore need to build our own module as replacement to Adobe Acrobat. Several open source tools are available for pdf to html conversion but these tools do not preserve the cell structure in a table. Our goal in this project is to develop a tool that extracts text, figures and tables in a pdf document and maintains the structure of the document using a tree data structure.

This project is using the table-extraction tool (https://github.com/xiao-cheng/table-extraction).

## Dependencies

```pip install -r requirements.txt```

```./install-poppler.sh```

## Environment variables

First, set environment variables. The ```DATAPATH``` folder should contain the pdf files that need to be processed.

```source set_env.sh```
