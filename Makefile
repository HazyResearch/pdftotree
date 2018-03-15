dev: docs
	pip install -e .

test:
	pytest tests -rsXx

docs:
	pandoc --from=markdown --to=rst --output=README.rst README.md

clean:
	rm README.rst

.PHONY: dev test docs clean
