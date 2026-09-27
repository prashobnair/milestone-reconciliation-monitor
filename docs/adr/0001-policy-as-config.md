# ADR 0001: Keep review policy in local validated config

Status: accepted for the offline prototype (2026-09-27).

The reconciliation engine needs one repeatable default yet a PM may use a different stale threshold or status interpretation. `policy.yaml` is JSON-compatible YAML, parsed with Python's standard library and validated before reconciliation or any ledger write. It names `stale_after_days`, sorted unique `stale_age_bands` beginning at that threshold, and ordered `status_compatible` pairs. Defaults remain seven days, bands 7/14/30, and `planned`/`in_progress` compatible with `open_unknown`. Unknown keys and malformed values fail closed.

This avoids a runtime YAML dependency and makes policy changes reviewable in git. It does not make policy changes automatically migrate an existing ledger or notify anyone. The Zoho-shaped portfolio importer uses the default policy for this demonstration, not an independently configured one; a future connected adapter will need explicit policy versioning and a separately reviewed migration path.
