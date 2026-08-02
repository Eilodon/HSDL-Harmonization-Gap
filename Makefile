PYTHON ?= python3

.PHONY: test reproduce verify-sources clean

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

reproduce: test
	mkdir -p generated
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode legacy --policies policies/legacy_v11.json > generated/legacy-v11-results.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode decision33 --catalog catalogs/vn_decision_33_2026.csv > generated/decision33-ingestion-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode current-context --catalog catalogs/vn_decision_33_2026.csv > generated/decision33-current-context.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode typed-alignment --policies policies/legacy_v11.json --crosswalk alignments/legacy_obligation_crosswalk.json --semantics alignments/legacy_duty_semantics.json > generated/typed-alignment-audit.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode asean-ontology --asean-ontology asean/guide_ontology_2024_2025.json > generated/asean-ontology-audit.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode emit-hsdl --policies policies/legacy_v11.json --semantics alignments/legacy_duty_semantics.json > generated/legacy-v11.hsdl
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode hsdl-differential --policies policies/legacy_v11.json --semantics alignments/legacy_duty_semantics.json > generated/hsdl-differential-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode typed-cover --policies policies/legacy_v11.json --semantics alignments/legacy_duty_semantics.json > generated/typed-cover-audit.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode provision-audit --policies policies/legacy_v11.json --provision-audit sources/reviews/legacy_v11_provision_audit.json > generated/provision-audit-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode review-readiness --review-template reviews/independent_legal_review_template.json --provision-audit sources/reviews/legacy_v11_provision_audit.json > generated/independent-review-readiness.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode migration-plan --provision-audit sources/reviews/legacy_v11_provision_audit.json > generated/current-profile-migration-plan.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode gate-status --policies policies/legacy_v11.json --semantics alignments/legacy_duty_semantics.json --catalog catalogs/vn_decision_33_2026.csv --provision-audit sources/reviews/legacy_v11_provision_audit.json --review-template reviews/independent_legal_review_template.json > generated/research-gate-status.json

verify-sources:
	mkdir -p generated
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode verify-sources --targets sources/official_pdf_targets.json --lock sources/official_pdf_lock_2026-08-02.json > generated/source-provenance-verification.json

clean:
	rm -rf generated
