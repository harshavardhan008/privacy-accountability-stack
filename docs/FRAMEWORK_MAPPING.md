# Framework mapping

How the stack's controls line up with frameworks people already use. This is evidence support, not a compliance certification and not legal advice. Check the current text of each framework before relying on a mapping.

| Control in this repository | What it produces | Related provisions and themes |
|---|---|---|
| Purpose Pass carried through every call | The stated purpose is checked at each tool call | GDPR Article 5(1)(b), purpose limitation |
| Purpose gateway minimization | The agent receives only the fields its purpose needs | GDPR Article 5(1)(c), data minimisation; Article 25, data protection by design |
| Sink rules and redaction | Text going to a ticket, vendor, or notes field is checked against what that destination may hold | GDPR Article 5(1)(f) and Article 32, security of processing |
| Human approval for writes and sends | A named person approves actions that change data or leave the boundary | EU AI Act Article 14, human oversight, for systems in its scope |
| Action Record and tamper-evident ledger | One record per action, including denials, with classes and hashes only | GDPR Article 5(2), accountability; EU AI Act Article 12, record-keeping, for high-risk systems in its scope |
| Action Lineage and consent withdrawal impact | Which request, agent, and handoff touched whose data | GDPR Articles 7(3) and 17, withdrawal and erasure; Article 30 is the controller's own record of processing, which these records can inform but do not replace |
| Graduation ladder | An agent earns production access in stages on synthetic data first | NIST AI RMF, Manage and Govern functions |
| Clinic Exam and scorecard | Repeatable measurement of leak rates and record completeness | NIST AI RMF, Measure function |

## Agent security lists

OWASP publishes a Top 10 for Agentic Applications. This repository's four quiet leaks relate to themes there, such as excessive tool scope, memory and context risks, and trust between agents. Item names and numbers change, so map them against the current list yourself.

## Timing note

The EU Digital Omnibus proposal moved high-risk AI Act obligations later (Annex III systems to December 2027 and Annex I systems to August 2028 in the version I reviewed). GDPR duties did not move. Verify the current dates.
