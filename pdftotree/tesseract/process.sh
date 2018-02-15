#! /bin/bash

tesseract $1/png/page_$2.png $1/tesseract/page_$2.html hocr
mv $1/tesseract/page_$2.html.hocr $1/tesseract/page_$2.html
#python annotate.py $1/tesseract/page_$2.html $1/annotated/page_$2.png
python ./../tesseract/annotate.py $1/tesseract/page_$2.html $1/annotated/page_$2.png
