# Standards engagement

This project is meant to be used and challenged by others. This note lists where it connects to existing work and how to contribute back. The mapping below is indicative. It is not legal advice and not a compliance claim.

## Where each part lines up

| Part of this project | Related concept |
|---|---|
| Purpose pass, purpose check at each call | GDPR Art. 5(1)(b) purpose limitation |
| Minimization at the tool boundary, sink redaction | GDPR Art. 5(1)(c) data minimization; Art. 25 data protection by design |
| Action Record, ledger | GDPR Art. 5(2) accountability and Art. 30 records of processing; EU AI Act Art. 12 record-keeping for high-risk systems |
| Approval field, graduation ladder | EU AI Act Art. 14 human oversight |
| Consent reference, withdrawal impact | GDPR Art. 7 conditions for consent and Art. 17 erasure |
| Synthetic sandbox (Layer 0) | NIST AI RMF Map and Measure functions; testing practices in ISO/IEC 42001 |
| Agent identity | Out of scope here. See NIST NCCoE work on agent identity and authorization |
| Agent security risks | Out of scope here. See OWASP Top 10 for Agentic Applications |

High-risk obligations under the EU AI Act were moved by the Digital Omnibus to 2 December 2027 for stand-alone systems and 2 August 2028 for embedded ones. GDPR duties already apply to agents today.

## How to contribute outward

* **OWASP GenAI Security Project.** The project invites contributors and reviewers. A purpose-and-proof view of agent privacy could be offered as a guidance contribution.
* **NIST NCCoE agent identity and authorization project.** NIST published a concept paper in February 2026 and said a project would follow. Watch for the call for collaborators and public comment, and send the Action Record as input on accountability.
* **IEEE.** Ask whether a study group or Industry Connections activity on agent action records would be welcome. Related existing work on data privacy process includes IEEE 7002-2022.
* **Open tracker.** Issues labeled `standards-feedback` collect field-level feedback on the record and the ladder.

## What would make this stronger

Independent use by people who are not the author, a field-by-field mapping reviewed by a privacy lawyer, a comparison with agent logging formats in common frameworks, and results from real deployments shared by the teams who ran them.
