# API contracts

There are no live HTTP or Zoho endpoints in this release. Both CLIs consume local synthetic JSON and the Zoho-shaped mapper is a fixture translator, not an authenticated adapter. `schema_version` in outputs is `1` and is independent of the package version.

The input snapshot has exactly `schema_version`, `project_id`, `as_of`, `plan`, and `tracker`. Timestamps must be ISO 8601 with an offset, and milestone keys must be unique within each source. Review findings preserve the plan/tracker source; missing and stale records require review. The local state CLI stores transitions in SQLite but does not send them. `policy.yaml` controls the default stale rule and compatible status pairs; see [ADR 0001](adr/0001-policy-as-config.md).

The [Zoho Projects-shaped fixture](ZOHO_SAMPLE.md) uses fields inspired by the published [Milestones API examples](https://www.zoho.com/projects/help/rest-api/milestones-api.html), not a claim of current live response parity. Endpoint version, OAuth scopes, data center, pagination, rate limits, source timestamp availability and authorization are unverified and must be checked against official docs and a consenting development org before live mode. No live network request is permitted by this prototype.
