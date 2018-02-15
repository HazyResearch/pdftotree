#! /bin/bash

for i in dev_results/dev/pdf/*; do
	echo $i/
	python do_extract.py $i/
done
