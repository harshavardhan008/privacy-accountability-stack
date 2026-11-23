# Agent Privacy Clinic

A five-minute checkup for AI agents that touch personal data. Part of the [Privacy Accountability Stack](../README.md).

## The five checks

Answer yes or no for one agent. See [`CHECKLIST.md`](CHECKLIST.md) for the full wording and what each check means.

1. **Purpose.** Every request carries a purpose, checked at each tool call.
2. **Minimization.** Each tool returns only the fields that purpose needs.
3. **Record.** A record is written for every action, including denied ones, without storing the data itself.
4. **Approval.** A person approves writes and sends that leave your boundary.
5. **Sandbox.** The agent ran on synthetic data with real business rules before real data.

## What is here

| File | Purpose |
|---|---|
| `index.html` | The scorecard. Runs in the browser and stores nothing. It produces a result code such as `AAR1\|status\|bits\|role`. |
| `CHECKLIST.md` | The printable checklist. |
| `METHOD.md` | How to run the scorecard as an anonymous survey, including small-group suppression (groups under 5 are not reported) and the self-selected sample caveat. |
| `tools/make_qr.py`, `tools/make_card.py` | Make a QR code and a printable card for a talk or workshop. |
| `clinic_exam/`, `tests/`, `results/` | The Clinic Exam: probes, four agents, statistics, report, tests, and saved results. |
| `exam/index.html` | The exam in the browser. |
| `responses_example.txt` | Synthetic example codes for trying the aggregator. Delete before collecting real data. |

## Clinic Exam

The checkup asks people. The exam tests agents. It runs the same leak attacks against four agents on synthetic data and reports the difference with 95% Wilson intervals:

1. an unguarded agent
2. an agent with only a simple text scanner (emails and phone numbers)
3. an agent behind the purpose gateway
4. the gateway plus the scanner

```bash
cd agent-privacy-clinic
pip install -e ../agent-action-record
python -m clinic_exam --customers 50 --out results
```

Or run it in the browser: https://harshavardhan008.github.io/privacy-accountability-stack/agent-privacy-clinic/exam/

The exam also reports what gets past the gateway: disguised, split, and carried-over copies of a value, and a forged Purpose Pass. A text scanner catches one case the gateway cannot (data the customer typed into the chat). Results are in `results/exam.md`. The probes were written by the author of the gateway and the trials vary the synthetic customer, not the mechanism, so the intervals describe this test set and not the real world. Method and mappings to GDPR, the EU AI Act, and NIST AI RMF are in [`../docs/FRAMEWORK_MAPPING.md`](../docs/FRAMEWORK_MAPPING.md).

## Aggregate results

```bash
cd ../agent-action-record
pip install -e .
aar score ../agent-privacy-clinic/responses_example.txt
```

## Hosting the scorecard

Enable GitHub Pages for this repository (Settings, Pages, deploy from branch `main`, root folder). The scorecard is then at
`https://harshavardhan008.github.io/privacy-accountability-stack/agent-privacy-clinic/`.
GitHub Pages on a free account needs a public repository.

## Honest limits

The sample is self-selected, so results describe the people who chose to answer, not industry rates. The scorecard is a conversation starter, not a certification.
