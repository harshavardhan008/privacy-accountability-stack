# The Privacy Accountability Stack

The stack organizes privacy accountability for enterprise AI into layers, each answering one question an auditor or a customer would ask.

## Training-time stack (published at GICITE 2026)

* **Layer 0, synthetic data.** Build, test, and train on synthetic data wherever possible, so real personal data stays out of early work.
* **Layer 1, lineage.** Track where data came from and where it went.
* **Layer 2, consent and minimization.** Check that each use is allowed and uses only what is needed.
* **Layer 3, audit.** Keep records that let you prove what happened.
* **Layer 4, regulatory alignment.** Map controls to the rules that apply.

## Runtime extension (this repository)

AI agents read records, call tools, write summaries, and hand work to other agents. Each step can touch personal data after the training pipeline is finished. The runtime extension carries the same layers into those steps.

| Stack layer | Runtime construct |
|---|---|
| Layer 0 | Graduation ladder: an agent earns production access on synthetic data first |
| Layer 1 | Action Lineage: which action came from which request, across handoffs |
| Layer 2 | Purpose Pass and purpose gateway: the reason for a request travels with it, and each tool returns only what that purpose needs |
| Layer 3 | Action Record and tamper-evident ledger: one record per action, including denied ones, storing classes and hashes, never personal values |
| Layer 4 | Mapping of the records to GDPR purpose limitation and accountability, and to the EU AI Act record-keeping duties |

## Four quiet leaks the runtime extension addresses

1. Wide tool scope
2. Context carry-over between requests
3. Summaries that become new copies of personal data
4. Purpose lost in handoffs between agents
