PYTHON ?= python3

.PHONY: test reproduce clean

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

reproduce: test
	mkdir -p generated
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode legacy --policies policies/legacy_v11.json > generated/legacy-v11-results.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode decision33 --catalog catalogs/vn_decision_33_2026.csv > generated/decision33-ingestion-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode typed-alignment --policies policies/legacy_v11.json --crosswalk alignments/legacy_obligation_crosswalk.json --semantics alignments/legacy_duty_semantics.json > generated/typed-alignment-audit.json

clean:
	rm -rf generated
