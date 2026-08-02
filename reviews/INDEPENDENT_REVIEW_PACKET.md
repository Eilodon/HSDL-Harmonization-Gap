# Independent legal and policy review packet

## Review objective

This packet asks an independent reviewer to assess the source-to-encoding judgments that currently block promotion of the frozen hackathon model into a current-law comparative analysis.

The reviewer is **not** being asked to verify arithmetic, Python quality or historical reproduction. Those are covered by automated tests. The reviewer is being asked to decide whether the legal and policy objects have been interpreted and paired correctly.

## Materials

Review these repository artifacts together:

1. `sources/official_pdf_lock_2026-08-02.json` — exact official PDF identities.
2. `sources/current_freeze_2026-08-02.json` — legal-source and gate status.
3. `sources/reviews/vn_decision_33_2026.visual.json` — signed-PDF route-table visual review.
4. `sources/reviews/legacy_v11_provision_audit.json` — rule-by-rule source audit.
5. `alignments/legacy_obligation_crosswalk.json` — proposed EU–Vietnam pairing judgments.
6. `asean/guide_ontology_2024_2025.json` — typed ASEAN ontology.
7. `reviews/independent_legal_review_template.json` — required structured response.

The frozen policy bundle in `policies/legacy_v11.json` is historical evidence, not the proposed final encoding.

## Source custody and evidence limitations

The official PDFs are checksum-pinned but not vendored in Git. The project has verified that live official transports reproduce the pinned bytes, and checksum-verified derivative pages were generated for visual review. Cryptographic signature validation and project-controlled durable custody remain separate gates.

The reviewer should use the official instruments and the exact provision locators in the provision audit. Any disagreement should identify the provision, preferred interpretation and resulting change to the typed rule or crosswalk.

## Required questions

### Vietnam Article 10(2)

Does the provision support a deployer responsibility to coordinate with the provider for reclassification after modifications, integration or functional changes that create new or higher risk? Is a provider-only obligor set wrong?

### Vietnam Article 10(5)

Should high-risk inspection and medium-risk monitoring be represented as duties of a regulated entity, powers or consequences exercised by a competent authority, or a mixture of triggers and mechanisms? Which actor labels are defensible?

### Vietnam Article 13 and Decision 33

Confirm or reject:

- point-a catalog systems require certification by a registered or recognised conformity-assessment organisation;
- point-b systems permit provider self-assessment or engagement of such an organisation;
- the recorded route split is 6 point-a rows and 40 point-b rows;
- Article 13(1) does **not** support automatic reuse of a prior sector certification.

Explain how provider, assessor and certifier roles should be represented.

### Decree 142 Article 19

Identify each distinct duty and actor for:

- incident recording;
- immediate response and mitigation;
- provider notification;
- provider technical remediation;
- provider–deployer coordination;
- preliminary reporting;
- the condition under which a deployer fallback applies;
- reporting deadlines and record retention.

Confirm whether the frozen generic G6 `control_risk` rule should be withdrawn.

### Vietnam Article 4(2)

Is the universal human-control provision best treated as a binding general principle rather than an exact substitute for every technical design or deployment duty in EU Articles 14 and 26?

### EU rule scope

Confirm the need to:

- remove the frozen shortcut that extends high-risk obligations to the `Unacceptable` tier;
- retain category- and procedure-specific distinctions in Article 43;
- type Article 14 provider design duties separately from Article 26 deployer duties;
- retain Article 26(6) control and retention conditions for logs;
- preserve Article 50 exceptions, timing and accessibility.

### Exact crosswalk

For each proposed EU–Vietnam pair, decide whether it is:

- the same exact normative slot;
- a compatible but analogical duty;
- a broad protected-interest match;
- a cross-functional bundle that must not generate an actor-mismatch statistic;
- not comparable.

### ASEAN object typing

Confirm whether the selected objects are voluntary principles and policy recommendations rather than universally triggered entity-level legal rules. In particular, review the treatment of transparency, human-centricity, accountability and content provenance.

## Required response

Complete `reviews/independent_legal_review_template.json`. Every required question needs:

- a decision;
- concise reasoning;
- any required encoding or manuscript change.

The reviewer must also provide identity, professional role, jurisdictions reviewed, conflict disclosure, independence attestation, overall decision and dated signature information.

A partially completed template will not close the gate.

## Decision options

Recommended values for each `reviewer_decision` are:

- `AGREE`
- `AGREE_WITH_NARROWING`
- `DISAGREE`
- `INSUFFICIENT_SOURCE`
- `OUTSIDE_REVIEWER_SCOPE`

Recommended overall decisions are:

- `APPROVE_FOR_REENCODING`
- `APPROVE_WITH_REQUIRED_CHANGES`
- `REQUIRES_FURTHER_SOURCE_WORK`
- `REJECT_CURRENT_CROSSWALK`

## What approval means

Approval does not validate the old numerical results. It authorises the project to implement a reviewed current-law encoding and rerun the analysis. New quantitative and manuscript claims remain blocked until that implementation passes differential, regression and provenance gates.
