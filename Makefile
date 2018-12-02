TESTDATA=tests/input

dev: 
	pip install -r requirements-dev.txt
	pip install -e .
	pre-commit install

test: $(TESTDATA)/paleo_visual_model.h5 dev check
	pytest tests 

$(TESTDATA)/paleo_visual_model.h5:
	cd tests/input/ && ./download_vision_model.sh

check:
	isort -rc -c bin/
	isort -rc -c tests/
	isort -rc -c pdftotree/
	black bin/ --check
	black tests/ --check
	black pdftotree/ --check
	flake8 pdftotree/
	flake8 bin/
	flake8 tests/

clean:
	rm -f $(TESTDATA)/paleo_visual_model.h5
	pip uninstall pdftotree
	rm -r pdftotree.egg-info

.PHONY: dev test clean check
