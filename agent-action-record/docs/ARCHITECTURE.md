# Architecture

## Flow of one tool call

```
 agent runtime
      |  PurposePass(request_id, delegator, purpose, agent, environment)
      v
 +--------------------------- gateway ---------------------------+
 | 1 purpose known?            -> deny: unknown_purpose          |
 | 2 tool allowed for purpose? -> deny: tool_not_permitted...    |
 | 3 subject withdrew consent? -> deny: consent_withdrawn        |
 | 4 shadow rung write/send?   -> deny: shadow_proposal          |
 | 5 approval needed?          -> deny: approval_required        |
 | 6 run the tool                                                |
 | 7 drop fields the purpose does not need   (minimized)         |
 | 8 remember which values were released     (for sink checks)   |
 | 9 write an Action Record to the ledger    (every outcome)     |
 +----------------------------------------------------------------+
      |  only the minimized fields
      v
 agent  ---- emit(text) ---->  sink check: redact released values
                               the sink may not hold, then record
```

## Components

* **ConsentRegistry.** Purposes, the data classes each may see, the tools and operations each may use, and withdrawn consent. In production this would front your consent management system.
* **ToolSpec.** Wraps a tool with its operation type and a map from output field to data class. Classifying fields is the real work of adopting this.
* **SinkSpec.** Describes anywhere an agent can write text. Each sink lists the classes it may hold.
* **Gateway.** The checkpoint described above. Also handles handoffs, scoped memory, and per-request cleanup.
* **Ledger.** Hash-chained, append-only log of records.
* **Lineage, ladder, scorecard.** Read the records and answer questions about them.

## Handoffs

`delegate()` creates a new Purpose Pass for the receiving agent. The purpose cannot change and the number of hops is capped. A handoff is itself recorded, so the chain of custody is visible.

## Memory

`remember()` and `recall()` scope agent memory to one request. A read of another request's memory is denied and recorded. Call `end_request()` when a request finishes.

## What this does not cover

| Gap | Why it matters | What to do |
|---|---|---|
| Direct access that skips the gateway | The gateway sees only what goes through it | Put the gateway where the agent has no other route to data: network policy, credentials held by the gateway, not the agent |
| Exact-match sink checks | Paraphrased or re-encoded values pass | Add classifiers, format-aware detectors, and sink-side controls |
| Prompt injection and tool poisoning | A manipulated agent can still ask for allowed data for a bad reason | Use the security controls in the OWASP agentic guidance |
| Data held by the model provider | Context sent to a model leaves your boundary | Minimize what enters context, and review provider terms |
| Clock and log integrity | A privileged attacker can rewrite a chain | Anchor the head hash externally and restrict ledger write access |
| Classification errors | A field mapped to the wrong class is released | Review the field map like code, and test it with synthetic data |

## Integration notes

The gateway is a library, but the pattern is a proxy. With tool protocols such as MCP, the same checks can run in a server that sits between the agent and the real tools. The interface to preserve is: every call carries a purpose, every response is minimized, every outcome is recorded.

## Design choices

* **Denials are records.** An agent repeatedly hitting a wall is information.
* **Hashes, not copies.** The audit trail must not become a new store of the data it protects.
* **Plain dataclasses, no dependencies.** The code is meant to be read in an afternoon.
