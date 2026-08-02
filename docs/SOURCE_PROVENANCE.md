# Official source provenance

This change set separates four facts that must not be conflated:

1. an official URL was identified;
2. bytes were successfully acquired from that URL;
3. the acquired bytes were cryptographically fingerprinted;
4. the legal text, signature, tables, and provision locators were independently reviewed.

A successful acquisition run proves only items 1–3. It does not perform legal review or visual verification.

## Target bundle

`sources/official_pdf_targets.json` is the network-acquisition input. Every target must:

- use HTTPS;
- identify one official PDF endpoint;
- have a unique source identifier and URL;
- declare a positive page count discovered from the official endpoint;
- state whether the source is load-bearing for current-law claims.

The declared page count is metadata, not a page recount by the dependency-free acquisition runner.

## Acquisition report

Run:

```bash
PYTHONPATH=src python -m hsdl_gap \
  --mode acquire-sources \
  --targets sources/official_pdf_targets.json \
  > generated/source-provenance-candidate.json
```

For each successful fetch, the report records:

- requested and final URL;
- HTTP status and content type;
- byte size;
- SHA-256 digest;
- PDF magic-byte verification;
- artifact-custody status;
- visual-review status.

The runner refuses non-PDF payloads, duplicate source identifiers, duplicate URLs, non-HTTPS targets, and files larger than the configured maximum.

## Custody states

The initial acquisition state is `HASH_ONLY_NOT_VENDORED`. This means the bytes were fetched and hashed during the run but are not stored in the Git repository. A digest alone is not an immutable archive. A future archival step may use a release asset, institutional repository, or other durable store and must record that custody transition explicitly.

## Promotion gate

A candidate report may be converted into a pinned lock only when:

- all required sources were acquired;
- every artifact began with PDF magic bytes;
- no acquisition errors remain;
- each digest is reviewed before committing;
- the lock distinguishes checksum verification from legal and visual review.

Current-law quantitative claims remain blocked until the separate provision-level and legal-review gates pass.
