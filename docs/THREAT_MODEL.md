# Threat model: offline milestone review

| STRIDE concern | Boundary | Current guard | Remaining limit |
|---|---|---|---|
| Spoofing | Local fixture to CLI | No claim that input represents an authenticated Zoho project | File author is not verified |
| Tampering | Snapshot and policy | Exact field validation, timezone-aware timestamps, fail-closed policy; ledger rejects older observations | No signed baseline or tamper-evident storage |
| Repudiation | Local review history | SQLite stores observed transitions and source-labeled findings | No reviewer identity or audit-grade attribution |
| Information disclosure | Fixture, ledger, CI artifacts | Fictional examples only, no remote connector or notification | Local SQLite file has no encryption or access-control layer |
| Denial of service | CLI and SQLite | Bounded record keys, local-only execution | No workload quotas or concurrency design |
| Elevation of privilege | Future connector/notification | No credentials, live endpoint, scheduler or send path shipped | Require least-privilege scopes and explicit recipient approval before adding them |

Do not import employer/customer records or expose the local database as a service.
