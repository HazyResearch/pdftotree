#! /bin/bash

for i in dev/pdf/*; do
	echo $i
	sh ./preprocess.sh ./dev_results/$i $i
done
