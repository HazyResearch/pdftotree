TESTDATA=tests/input

dev: 
	pip install -e .

test: $(TESTDATA)/paleo_visual_model.h5
	python setup.py test

$(TESTDATA)/paleo_visual_model.h5:
	cd tests/input/ && ./download_vision_model.sh

clean:
	rm -f README.rst
	rm -f $(TESTDATA)/paleo_visual_model.h5

.PHONY: dev test clean
