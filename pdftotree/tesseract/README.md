# tesseract-tables
A tool for extracting tables, figures, maps, and pictures from PDFs using Tesseract

## preprocess.sh
Script for prepping a PDF for table extraction. Converts each page of the PDF to a PNG with Ghostscript, then runs the PNGs through Tesseract. Also runs each page through `annotate.py` to assist in debugging.

#### Example usage

````
./preprocess.sh ./my_document_processed my_document.pdf
````

This creates the file structure necessary for extraction:
````
document_name
  annotated (pngs of what tesseract sees)
  png (each page of the PDF as a PNG image)
  tables (extractions)
  tesseract (HTML for each page produced by tesseract)
  orig.pdf (The original document)
  text.txt (The extracted text layer)
````

## do_extract.py
Script for processing the output of `pdf2hocr`.

#### Example usage

````
python do_extract.py ~/Documents/doc
````

## annotate.py
Creates a PNG that shows the areas of a page identified by Tesseract. Useful for debugging.

## helpers.py
Various functions for processing tables.

## table_extractor.py
Entry script to table extraction.

#### extract_tables(document_path)
Process a document for tables. Pass it a path to a document that has been pre-processed with pdf2hocr
