PYTHON ?= python3

.PHONY: test reproduce verify-sources clean

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

reproduce: test
	mkdir -p generated
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode legacy --policies policies/legacy_v11.json > generated/legacy-v11-results.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode decision33 --catalog catalogs/vn_decision_33_2026.csv > generated/decision33-ingestion-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode typed-alignment --policies policies/legacy_v11.json --crosswalk alignments/legacy_obligation_crosswalk.json --semantics alignments/legacy_duty_semantics.json > generated/typed-alignment-audit.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode asean-ontology --asean-ontology asean/guide_ontology_2024_2025.json > generated/asean-ontology-audit.json

verify-sources:
	mkdir -p generated
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode verify-sources --targets sources/official_pdf_targets.json --lock sources/official_pdf_lock_2026-08-02.json > generated/source-provenance-verification.json

clean:
	rm -rf generated
