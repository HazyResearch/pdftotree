TESTDATA=tests/input

dev: 
	pip install -e .

test: $(TESTDATA)/paleo_visual_model.h5 dev check
	python setup.py test

$(TESTDATA)/paleo_visual_model.h5:
	cd tests/input/ && ./download_vision_model.sh

check:
	flake8 pdftotree --count --max-line-length=127 --statistics --ignore=E731,W503

clean:
	rm -f $(TESTDATA)/paleo_visual_model.h5
	pip uninstall pdftotree
	rm -r pdftotree.egg-info

.PHONY: dev test clean check
