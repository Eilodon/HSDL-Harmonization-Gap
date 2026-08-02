# P0 engineering foundation acceptance criteria

This pull request is complete when:

- the existing legacy and canonical tests remain green;
- the new engineering foundation tests pass;
- every schema in `schemas/` declares Draft 2020-12 and has a unique `$id`;
- missing condition facts evaluate to `UNKNOWN`, not `FALSE`;
- generated boundary fixtures retain parent and mutation provenance;
- model-relative experiment reports include profile/corpus hashes, assumptions, explicit measures and unknown handling;
- experiment reports cannot assert independent legal validation;
- `make verify` and `make reproduce` run the new checks and produce the engineering demonstration artifacts;
- the frozen v11 profile and provisional current-law safety flags remain unchanged.
