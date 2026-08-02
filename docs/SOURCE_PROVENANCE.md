# Official source provenance

This change set separates four facts that must not be conflated:

1. an official URL was identified;
2. bytes were successfully acquired from that URL;
3. the acquired bytes were cryptographically fingerprinted and matched a pinned lock;
4. the legal text, signature, tables, and provision locators were independently reviewed.

A successful checksum verification proves only items 1–3. It does not perform legal review, signature validation, or visual verification.

## Target bundle

`sources/official_pdf_targets.json` is the network-acquisition input. Every target must:

- use HTTPS;
- identify one official PDF endpoint;
- have a unique source identifier and URL;
- declare a positive page count discovered from the official endpoint;
- state whether the source is load-bearing for current-law claims.

The declared page count is metadata, not a page recount by the dependency-free acquisition runner.

## Acquisition

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

## Pinned lock

`sources/official_pdf_lock_2026-08-02.json` records the six official PDFs acquired by GitHub Actions on 2026-08-02. The lock includes the workflow run, head commit, workflow-artifact identity, byte size, SHA-256 digest, declared page count, and source profile for every PDF.

The initial acquisition completed six of six targets with no errors. A separate CI run then fetched all six endpoints again and produced six `VERIFIED` records with no checksum, byte-size, URL, page-count, or profile mismatch.

## Verification

Run:

```bash
PYTHONPATH=src python -m hsdl_gap \
  --mode verify-sources \
  --targets sources/official_pdf_targets.json \
  --lock sources/official_pdf_lock_2026-08-02.json \
  > generated/source-provenance-verification.json
```

Verification fails when:

- a required PDF cannot be acquired;
- an endpoint returns a non-PDF payload;
- the acquired SHA-256 or byte size differs from the lock;
- source metadata differs from the lock;
- a locked source is missing or an unexpected source appears.

GitHub Actions runs this verification as a separate required job. The report is uploaded as a workflow artifact even when verification fails.

## Custody state

The current custody state is `HASH_ONLY_NOT_VENDORED`. The bytes were fetched twice and their identities were pinned, but the PDFs are not stored in the Git repository or another durable archive controlled by the project. A digest alone is not an immutable archive.

A future custody step may use a release asset, institutional repository, or other durable store. That transition must be recorded explicitly and must not overwrite the historical hash-only state.

## Remaining gates

The checksum gate is complete, but current-law quantitative claims remain blocked until all load-bearing sources also pass:

- durable artifact-custody decision;
- visual PDF review where tables or scanned pages matter;
- provision-level locators and legal interpretation audit;
- second-reviewer sign-off;
- regeneration of current-law results from the reviewed encoding.
