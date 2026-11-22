# Graduation ladder

An agent earns access to real personal data in four rungs. This is Layer 0 of the accountability stack applied to agents: start on synthetic data.

| Rung | Data | Who acts | Writes and sends |
|---|---|---|---|
| 1. Sandbox | Synthetic customers with realistic business rules | The agent | Allowed, no approval needed (nothing real is touched) |
| 2. Shadow | Real data, masked where possible | A person acts, the agent proposes | Recorded as proposals, never executed |
| 3. Limited | Production | The agent, with human approval on every write or send | Approved, and each approval is recorded |
| 4. Production | Production | The agent | Policy-based approval, sampled audits |

## Why the sandbox must have real business rules

Synthetic data that looks right statistically is not enough for agents. An agent calls tools, and tools enforce business logic: a refund needs an order, points need an eligible purchase, a ticket needs an account. If the synthetic customers break those rules, the agent learns nothing useful about how it will behave. Build the sandbox from the same rule set as production, with fake people.

## Exit criteria (starting points)

Run `aar graduate ledger.jsonl --rung <current>`. Thresholds live in `src/aar/ladder.py`.

| Move | Minimum actions | Max policy-denial rate | Also required |
|---|---|---|---|
| Sandbox to shadow | 50 | 10% | Ledger verified, every record valid |
| Shadow to limited | 100 | 5% | Reviewer agreement of at least 95% |
| Limited to production | 200 | 5% | Every allowed write or send has a recorded approval |

`shadow_proposal` denials are expected on the shadow rung and are not counted against the agent.

## Why a denial rate matters

An agent that keeps hitting policy walls is working outside its purpose or is poorly configured. Either way it is not ready for more access.

## Demotion triggers (suggested)

Move an agent down a rung when any of these happen: a new tool or data class is added, the model or prompt changes materially, the ledger fails verification, or a privacy incident traces back to it. Re-earn the rung with the same criteria.

## Tuning

These numbers are not a standard. A rewards lookup and a medical scheduling agent should not share thresholds. Set yours with your privacy, security, and product owners, and write the reasoning down.
