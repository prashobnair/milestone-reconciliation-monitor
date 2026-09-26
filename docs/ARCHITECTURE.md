# Initial design record

Input: a version-1 snapshot with project ID, explicit `as_of`, and plan/tracker lists keyed by milestone ID. Timestamps must carry a timezone; comparison normalizes instants to UTC. Exact plan/tracker ties need no review. Stale records, missing source rows, due-date, status and owner disagreements become findings with the milestone key and responsible plan-side owner. Invalid schema, duplicate milestone keys, naive timestamps and future updates fail rather than disappearing into an alert.

The first slice is pure and read-only. A later monitor should persist a fingerprint per finding, retain an audit history of observed and resolved states, and suppress duplicate notifications. Escalation must require a grounded owner and explicit channel scope. No production connection or notification is part of this repo yet.

The optional `zoho_sample` adapter handles fictional multi-project exports. It maps a documented subset of Zoho Projects milestone fields plus a clearly labeled supplemental `last_modified_time` and PM-owned baseline. Zoho `notcompleted` lacks a finer phase, so `open_unknown` is compatible with planned/in-progress without asserting equality to either. The raw internal snapshot fixture retains finer phase for separate status-drift tests. See `docs/ZOHO_SAMPLE.md` and the linked official reference.
