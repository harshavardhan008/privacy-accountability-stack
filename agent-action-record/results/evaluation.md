# Evaluation results (synthetic data, fixed seed)

200 synthetic customers, 8 fields each. Naive baseline = direct tool access, shared agent memory, unfiltered output.

| Scenario | Measure | Naive | Gateway |
|---|---|---|---|
| A. Wide tool scope | Fields beyond purpose need, per call | 6.0 | 0.0 |
| B. Context carry-over | Requests exposed to another customer's data | 199 of 200 | 0 of 200 |
| C. Summary copies | Disallowed values in ticket_system, per summary | 6.0 | 0.0 |
| C. Summary copies | Disallowed values in vendor_helpdesk, per summary | 7.0 | 0.0 |
| C. Summary copies | Disallowed values in notes_unclassified, per summary | 8.0 | 0.0 |
| D. Lost purpose | Purpose-widening handoffs accepted | 100% | 0% |

Utility: needed fields delivered 100%; legitimate requests denied 0; benign handoffs accepted 100 of 100.

| Tamper type | Detected, chain only | Detected, with anchored head |
|---|---|---|
| edit_field | 100% | 100% |
| delete_middle | 100% | 100% |
| swap_two | 100% | 100% |
| truncate_tail | 0% | 100% |
| rewrite_chain | 0% | 100% |

Overhead per call (20000 calls, Python 3.13.18, x86_64): direct tool 0.3 us, gateway with in-memory ledger 37.7 us, gateway with file ledger 53.4 us.
