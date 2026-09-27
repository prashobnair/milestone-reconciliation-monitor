# Local review state

## Why state is needed

A snapshot comparison alone prints the same mismatch on every run. That is useful for a one-time check but cannot distinguish new drift, a change to the same discrepancy, resolution, or recurrence. A PM needs those transitions before considering any alerting or follow-up.

## Data contract

`state_cli` uses the existing version-1 snapshot contract. It validates and reconciles the entire input before starting a SQLite write. One transaction then updates the project-specific current findings and history. An observation watermark prevents an older snapshot from rewriting a newer project state, even when the project has no active findings. Replaying the exact same observation updates `last_seen` but adds no duplicate history. Other projects are not touched.

A finding identity is a SHA-256 prefix over `(milestone key, kind, detail)`, so a changed due date or owner value is a `changed` transition on the same finding rather than a new incident. A separate full finding signature detects content changes. On resolution, the prior finding is kept in history; the current row is marked inactive. A recurrence uses `reopened`. Identities are internal to the local database and not stable IDs promised across schema versions. Hash collision is checked within a snapshot; the current design does not claim cryptographic integrity or authenticity of source records.

The `observations` table stores the latest `as_of` per project, `findings` stores the current state, and `history` records opened/aged/changed/resolved/reopened transitions. No scheduling, notification, delivery receipt, human acknowledgement, state migration tool, backup or retention policy is included. The demo does not resolve which source is right.

## Test evidence and operating limits

`uv run pytest` covers repeated snapshots, changed content, resolution and recurrence, invalid/older input rollback, project isolation, core time normalization and the Zoho-shaped fixture. The included snapshot starts with four findings; a second identical run returns four `unchanged` entries and only four history rows. The example SQLite file belongs outside the repo. This is a local, single-machine prototype. Before a production monitor: verify Zoho API mapping and pagination, design concurrency and backups, add retention and access controls, ground the intended owner/channel, and gain specific communication permission before any reminder is sent.

An age-only change in a stale finding is recorded as `aged`, keeping its full signature and daily history; it is not digest-eligible until its age crosses a later configured band (default 14 or 30 days). Opening, meaningful changes, resolution and recurrence remain digest-eligible. These fields are only local metadata, not delivered messages; `notification_count` is always zero. `policy.yaml` sets the stale threshold, strictly increasing bands beginning at that threshold, and allowed status compatibility pairs. Pass `--policy` to either CLI; invalid rules are rejected before a ledger write.
