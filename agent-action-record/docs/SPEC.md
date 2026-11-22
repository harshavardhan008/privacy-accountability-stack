# Action Record specification (v0.1)

An Action Record is written for every action an agent attempts through a tool, a sink, a handoff, or a memory operation. Denied attempts are recorded too. A record never contains personal data values.

## Content fields (the nine)

| Field | Type | Meaning |
|---|---|---|
| `request_id` | string, required | Ties every step in a chain to one starting request. |
| `delegator` | string, required | The person or system the agent acts for. |
| `agent_id`, `agent_version` | string, required | Which agent, and which model or configuration version. |
| `purpose` | string, required | Reason for the request, from a controlled list held by the consent registry. |
| `tool`, `operation` | string, required | What was called. Operation is one of `read`, `write`, `send`, `handoff`, `memory`. |
| `data_classes` | list of string | Classes of data released by the action, for example `identity`, `account`. Empty for denials. |
| `consent_ref` | string, required | Pointer to the consent or policy version that applied, for example `consent:v1:loyalty_support`. |
| `approval` | string or null | Who approved, if a person did. |
| `destination`, `retention_days` | string, integer | Where the output went (`internal`, `vendor`, `unclassified`) and how long it lives there. |

## Context and integrity fields

| Field | Meaning |
|---|---|
| `decision` | `allow`, `minimized` (allowed, with fields or values removed), or `deny`. |
| `reason` | Short code. See vocabulary below. |
| `environment` | Rung of the graduation ladder: `sandbox`, `shadow`, `limited`, `production`. |
| `subject_ref` | Salted, truncated hash of the data subject id. Lets you ask who was touched without storing who they are. |
| `parent_record_id` | The record that came before this one in the request, or the handoff that started it. |
| `input_hash`, `output_hash` | SHA-256 of the canonical JSON of the call and of what was released. For comparison, not for reading back. |
| `record_id`, `timestamp` | Identifier and Unix time. |

## Reason vocabulary

Allowed: `ok`, `dropped_N_fields`, `redacted_N_values`.
Denied: `unknown_purpose`, `unknown_tool`, `unknown_sink`, `tool_not_permitted_for_purpose`, `consent_withdrawn`, `approval_required`, `shadow_proposal`, `purpose_cannot_change_in_handoff`, `max_hops_exceeded`, `cross_request_memory`.

## Hashing and chaining

* Canonical JSON: keys sorted, separators `,` and `:`, UTF-8, no extra whitespace.
* `hash = SHA-256(canonical({"body": record, "prev": previous_hash}))`. The first `prev` is 64 zeros.
* Ledger file: one JSON object per line with `body`, `prev`, `hash`.

## What the chain does and does not prove

Detected from the file alone: edited entries, deleted entries from the middle, reordered entries.
Not detected from the file alone: removal of the last N entries, and a full rewrite of the chain from some point onward. Anchor the head hash outside the system that writes the log (a ticket, a signed message, a second system) and pass it to `aar verify --head`.

## Privacy rules for implementers

1. Never put personal data values in a record. Use classes and hashes.
2. Keep the `subject_ref` salt secret and rotate it on a schedule you can defend. Without the salt a reader cannot link a hash to a person.
3. Treat the ledger as personal data anyway if `subject_ref` plus other context could identify someone. Set a retention period for it.
4. Record denials. A pattern of denials is the earliest signal that an agent is working outside its purpose.

## Versioning

This is version 0.1. Fields may change before 1.0. Breaking changes will be listed in the changelog and the schema file will carry a version.
