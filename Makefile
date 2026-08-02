PYTHON ?= python3
NODE ?= node

.PHONY: test schema-check verify reproduce verify-sources clean

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

schema-check:
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.engineering_cli schema-inventory --schema-dir schemas > /dev/null

verify: test schema-check
	PYTHONPATH=src $(PYTHON) -m compileall -q src tests

reproduce: verify
	mkdir -p generated
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode legacy --policies policies/legacy_v11.json > generated/legacy-v11-results.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode decision33 --catalog catalogs/vn_decision_33_2026.csv > generated/decision33-ingestion-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode current-context --catalog catalogs/vn_decision_33_2026.csv > generated/decision33-current-context.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.decision33_context_v2 --catalog catalogs/vn_decision_33_2026.csv > generated/decision33-context-v2-corpus.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode current-candidate --current-candidate policies/current_candidate_graph_2026-08-02.json > generated/current-candidate-audit.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.candidate_ir > generated/current-candidate-ir-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.candidate_predicates > generated/source-derived-predicate-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.eu_context_v2 --mode corpus > generated/eu-article6-context-v2-corpus.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.eu_context_v2 --mode relation-scenarios > generated/decision33-eu-relation-scenarios.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.metric_analysis > generated/model-relative-metric-analysis.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.duty_signature > generated/operational-duty-signature-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.candidate_hsdl --emit > generated/current-candidate.hsdl
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.candidate_hsdl > generated/current-candidate-hsdl-differential-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.oracle_expected > generated/python-oracle-projection-report.json
	$(NODE) reference-engines/javascript/candidate_oracle.mjs \
		--hsdl generated/current-candidate.hsdl \
		--corpus generated/decision33-context-v2-corpus.json \
		--assumptions profiles/current-candidate-2026-08-02/engineering_assumptions.json \
		--expected generated/python-oracle-projection-report.json \
		> generated/independent-javascript-oracle-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.symbolic_region > generated/symbolic-catalog-region-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.symbolic_profile_v2 > generated/source-derived-symbolic-profile-v2-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.priority_v2 > generated/candidate-priority-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode typed-alignment --policies policies/legacy_v11.json --crosswalk alignments/legacy_obligation_crosswalk.json --semantics alignments/legacy_duty_semantics.json > generated/typed-alignment-audit.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode asean-ontology --asean-ontology asean/guide_ontology_2024_2025.json > generated/asean-ontology-audit.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode emit-hsdl --policies policies/legacy_v11.json --semantics alignments/legacy_duty_semantics.json > generated/legacy-v11.hsdl
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode hsdl-differential --policies policies/legacy_v11.json --semantics alignments/legacy_duty_semantics.json > generated/hsdl-differential-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode typed-cover --policies policies/legacy_v11.json --semantics alignments/legacy_duty_semantics.json > generated/typed-cover-audit.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode provision-audit --policies policies/legacy_v11.json --provision-audit sources/reviews/legacy_v11_provision_audit.json > generated/provision-audit-report.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode review-readiness --review-template reviews/independent_legal_review_template.json --provision-audit sources/reviews/legacy_v11_provision_audit.json > generated/independent-review-readiness.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode migration-plan --provision-audit sources/reviews/legacy_v11_provision_audit.json > generated/current-profile-migration-plan.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode gate-status --policies policies/legacy_v11.json --semantics alignments/legacy_duty_semantics.json --catalog catalogs/vn_decision_33_2026.csv --provision-audit sources/reviews/legacy_v11_provision_audit.json --review-template reviews/independent_legal_review_template.json > generated/research-gate-status.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.engineering_demo > generated/engineering-experiment-demo.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.engineering_cli schema-inventory --schema-dir schemas > generated/schema-inventory.json
	PYTHONPATH=src $(PYTHON) -m hsdl_gap.engineering_gates --artifact-dir generated > generated/engineering-gate-status.json

verify-sources:
	mkdir -p generated
	PYTHONPATH=src $(PYTHON) -m hsdl_gap --mode verify-sources --targets sources/official_pdf_targets.json --lock sources/official_pdf_lock_2026-08-02.json > generated/source-provenance-verification.json

clean:
	rm -rf generated
