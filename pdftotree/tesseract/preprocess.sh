#! /bin/bash

if [ $# -lt 2 ]
  then echo -e "Please provide an output directory and an input PDF. Example: pdf2hocr ./ocrd ~/Downloads/document.pdf"
  exit 1
fi

mkdir -p $1
mkdir -p $1/png
mkdir -p $1/tesseract
mkdir -p $1/annotated
mkdir -p $1/tables

gs -dBATCH -dNOPAUSE -sDEVICE=png16m -dGraphicsAlphaBits=4 -dTextAlphaBits=4 -r600 -sOutputFile="$1/png/page_%d.png" $2

cp $2 $1/orig.pdf
pdftotext $1/orig.pdf - -enc UTF-8 > $1/text.txt

ls $1/png | grep -o '[0-9]\+' | parallel -j 4 "./../tesseract/process.sh $1 {}"
# ls $1/png | grep -o '[0-9]\+' | parallel -j 4 "/home/pabajaj/table-extract/process.sh $1 {}"
