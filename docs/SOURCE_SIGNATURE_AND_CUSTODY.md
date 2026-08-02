# Official-source signature and custody pipeline

This pipeline separates four findings that must not be collapsed:

1. **Source identity** — bytes match the pinned size and SHA-256 acquired from a declared official transport.
2. **Embedded PDF signature presence** — Poppler `pdfsig` finds one or more signature fields.
3. **Cryptographic signature integrity** — the signed byte ranges and embedded CMS signature validate.
4. **Certificate trust** — the signer certificate chains to a trust anchor available to the runner.

A cryptographically valid signature with an unresolved certificate chain is reported as `EMBEDDED_SIGNATURE_VALID_TRUST_CHAIN_UNRESOLVED`; it is not reported as trusted.

## Signature profiles

Government-portal files ending in `.signed.pdf` require an embedded signature and valid cryptographic integrity under repository policy. Official Journal and ASEAN Secretariat PDFs do not require embedded signatures; their source identity remains anchored by official transport and the pinned lock.

The signature workflow acquires the exact locked bytes, runs `pdfsig`, and stages each PDF under a content-addressed path:

```text
objects/sha256/<first-two-hex>/<full-sha256>
```

The workflow artifact is temporary staging, not durable custody.

## External deposit promotion

The staging manifest can be deposited by the repository owner to Zenodo, OSF, an institutional repository, or another DOI/ARK provider. After deposit, copy the provider receipt into a real `external_deposit_receipt.json` based on the example file and verify it against the exact staged manifest.

Promotion requires:

- all six source objects;
- exact SHA-256 and byte-size matches;
- an HTTPS persistent URL;
- a persistent identifier;
- the exact manifest hash;
- a declared depositor;
- one receipt record per object.

Until a receipt passes verification, reports must retain:

```text
receipt_verified = false
durable_custody_established = false
```

## Boundaries

This pipeline verifies source bytes, embedded-signature evidence and custody receipts. It does not perform legal review, infer the legal effect of a digital signature, or authorise publication.
