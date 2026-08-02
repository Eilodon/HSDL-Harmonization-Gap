PYTHON ?= python3

.PHONY: test reproduce clean

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

reproduce: test
	mkdir -p generated
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --policies policies/legacy_v11.json > generated/legacy-v11-results.json

clean:
	rm -rf generated
