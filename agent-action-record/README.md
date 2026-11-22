# agent-action-record

Runtime module of the [Privacy Accountability Stack](../README.md).

Purpose-aware accountability for AI agents that touch personal data.

Reference implementation for the paper *Beyond the Pipeline: Runtime Privacy Accountability for Enterprise AI Agents* (ETIC 2026).

Identity tells you who the agent is. Security tells you what could go wrong. Privacy accountability tells you why the agent may touch this person's data, and whether you can prove it later. This project is a small, readable reference for that third question.

It extends a four-layer privacy accountability stack (lineage, consent and minimization, audit, regulatory alignment, with synthetic data as Layer 0) from training time to runtime, where agents act instead of only answer.

## What is in the box

| Piece | What it does | Where |
|---|---|---|
| **Action Record** | A fixed record written for every agent action, including denied ones. Stores classes and hashes, never personal values. | `src/aar/record.py`, `schema/`, `docs/SPEC.md` |
| **Purpose Pass and gateway** | The purpose of a request travels with it. A gateway in front of each tool checks purpose, consent, approval, and returns only the fields that purpose needs. | `src/aar/gateway.py` |
| **Tamper-evident ledger** | Hash-chained log of records. Detects edits, deletions, and reordering. | `src/aar/ledger.py` |
| **Action lineage** | Trace a request, list what touched a person, export a graph. Start here when someone withdraws consent. | `src/aar/lineage.py` |
| **Graduation ladder** | Four rungs from synthetic sandbox to production, with measurable exit criteria. | `src/aar/ladder.py`, `docs/GRADUATION_LADDER.md` |
| **Readiness scorecard** | A five-question anonymous self-check and an aggregator. | [`../agent-privacy-clinic/`](../agent-privacy-clinic/) |

## Quick start

```bash
pip install -e ".[dev]"
python examples/loyalty_points_demo.py     # the story from the talk
pytest                                      # 40+ tests
python bench/evaluate.py                    # synthetic evaluation, writes results/ (timings vary by machine)
```

```python
from aar import PurposePass
from examples.shared import make_customers, make_gateway

gw = make_gateway(make_customers(20))
p = PurposePass("req-001", "support-rep-17", "loyalty_support", "support-agent")

d = gw.call(p, "lookup_customer", "cust-0003")
print(sorted(d.data))            # ['loyalty_points', 'name']  (6 fields withheld)
print(d.record["decision"])      # 'minimized'
print(gw.ledger.verify().ok)     # True
```

Command line:

```bash
aar verify ledger.jsonl [--head <anchored hash>]
aar trace ledger.jsonl req-001
aar dot ledger.jsonl req-001 | dot -Tpng > lineage.png
aar graduate ledger.jsonl --rung sandbox
aar score responses.txt
```

Handout and QR tools (need `pip install reportlab "qrcode[pil]"`):

```bash
See ../agent-privacy-clinic/README.md for the QR code and print card.
```

## What the synthetic evaluation shows

200 synthetic customers, fixed seed, naive baseline versus the gateway. Full table in `results/evaluation.md`.

| Scenario | Naive | Gateway |
|---|---|---|
| Fields returned beyond what the purpose needs, per call | 6.0 | 0.0 |
| Requests exposed to another customer's data through shared memory | 199 of 200 | 0 of 200 |
| Disallowed values in a summary written to a vendor tool | 7.0 | 0.0 |
| Purpose-widening agent handoffs accepted | 100% | 0% |

Needed fields were still delivered 100% of the time and no legitimate request was denied. The ledger detected every edit, deletion, and reordering. It cannot see tail truncation or a full chain rewrite unless you anchor the head hash somewhere else.

These numbers show that the mechanisms work as designed on constructed scenarios. They say nothing about how common these failures are in real deployments. That is what the scorecard is for.

## Limits you should know about

* **Not a security boundary.** The gateway only controls what flows through it. An agent with direct database access bypasses it.
* **Sink checks use exact value matching.** A paraphrased or re-encoded value will not be caught. Treat it as a floor, not a filter you can rely on alone.
* **Prompt injection is out of scope.** See the OWASP Top 10 for Agentic Applications for that threat family.
* **Synthetic evaluation only.** No real customer data was used or measured.
* **Thresholds in the ladder are starting points**, not standards.

More in `docs/ARCHITECTURE.md`.

## Where this fits

NIST's AI Agent Standards Initiative and its NCCoE work on agent identity and authorization, and OWASP's Top 10 for Agentic Applications, cover identity and security. This project is complementary: it covers purpose, consent, and proof at the level of each action. See `docs/STANDARDS_ENGAGEMENT.md`.

## Contributing and citing

See `CONTRIBUTING.md`. If you use this in research or a talk, cite it using `CITATION.cff`.

Author: Harshavardhan Peddireddy. License: MIT.
