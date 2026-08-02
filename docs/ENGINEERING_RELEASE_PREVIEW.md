# Engineering release preview

## Purpose

The release preview packages model-relative engineering evidence into a deterministic, content-addressed archive without presenting it as a reviewed publication release.

## Package structure

Each selected source or generated artifact is stored once under:

```text
objects/sha256/<first-two-hash-characters>/<remaining-hash>
```

`manifest.json` preserves the original repository path, SHA-256, byte size, media type and object path. `ro-crate-metadata.json` describes the package as a research object and links every manifest entry to its content-addressed object.

The ZIP writer uses stable path ordering, fixed timestamps and fixed file permissions so identical inputs produce the same archive hash.

## Included evidence

The preview includes the candidate profile, Decision 33 catalog, engineering assumptions and bindings, schemas, metric and claim registries, official PDF locks/targets, current freeze metadata, generated reports and HSDL documents.

Official PDF bytes are not redistributed. The checksum lock is included so source identity remains visible.

## Verification

The verifier checks every object byte size and SHA-256, recomputes the manifest hash and requires RO-Crate metadata. Any tampered or missing object invalidates the package.

## Publication blockers

The preview intentionally records blockers including:

- durable PDF custody not established;
- PDF signature validation not established;
- no declared license file;
- no citation metadata;
- candidate predicates remain incomplete;
- full symbolic coverage remains incomplete.

## CI

The `engineering-release-preview` workflow performs a clean reproduction, validates the claim ledger, builds the package, verifies it and uploads the deterministic ZIP plus build/verification reports.

## Boundary

This is a verified local engineering package, not a durable institutional deposit. It neither authorises publication nor establishes legal validation.
