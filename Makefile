TESTDATA=tests/input

dev: docs
	pip install -e .

test: $(TESTDATA)/paleo_visual_model.h5 docs
	python setup.py test

docs:
	pandoc --from=markdown --to=rst --output=README.rst README.md

$(TESTDATA)/paleo_visual_model.h5:
	cd tests/input/ && ./download_vision_model.sh

clean:
	rm -f README.rst
	rm -f $(TESTDATA)/paleo_visual_model.h5

.PHONY: dev test docs clean
