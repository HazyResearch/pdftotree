TESTDATA=tests/input

dev: 
	pip install -r requirements-dev.txt
	pip install -e .
	pre-commit install

test: $(TESTDATA)/paleo_visual_model.h5 dev check
	pytest tests -v -rsXx

$(TESTDATA)/paleo_visual_model.h5:
	cd tests/input/ && ./download_vision_model.sh

check:
	isort -rc -c bin/
	isort -rc -c tests/
	isort -rc -c pdftotree/
	black bin/ --check
	black tests/ --check
	black pdftotree/ --check
	# This is our code-style check. We currently allow the following exceptions:
	#   - E731: do not assign a lambda expression, use a def
	#   - W503: line break before binary operator
	#   - E203: whitespace before ‘:’
	flake8 pdftotree/ --count --max-line-length=127 --statistics --ignore=E731,W503,E203
	flake8 bin/ --count --max-line-length=127 --statistics --ignore=E731,W503,E203
	flake8 tests/ --count --max-line-length=127 --statistics --ignore=E731,W503,E203

clean:
	rm -f $(TESTDATA)/paleo_visual_model.h5
	pip uninstall pdftotree
	rm -r pdftotree.egg-info

.PHONY: dev test clean check
