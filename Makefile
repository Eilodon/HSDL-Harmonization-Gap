PYTHON ?= python3

.PHONY: test reproduce clean

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

reproduce: test
	mkdir -p generated
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode legacy --policies policies/legacy_v11.json > generated/legacy-v11-results.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode decision33 --catalog catalogs/vn_decision_33_2026.csv > generated/decision33-ingestion-report.json

clean:
	rm -rf generated
