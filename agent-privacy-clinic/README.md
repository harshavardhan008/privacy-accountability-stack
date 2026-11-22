# Agent Privacy Clinic

A five-minute checkup for AI agents that touch personal data. Part of the [Privacy Accountability Stack](../README.md).

## The five checks

Answer yes or no for one agent. See [`CHECKLIST.md`](CHECKLIST.md) for the full wording and what each check means.

1. A stated purpose travels with every request
2. Each tool returns only the fields that purpose needs
3. Each action leaves a record of classes and hashes, never personal values
4. Records are tamper-evident
5. The agent earned production access on synthetic data first

## What is here

| File | Purpose |
|---|---|
| `index.html` | The scorecard. Runs in the browser and stores nothing. It produces a result code such as `AAR1\|status\|bits\|role`. |
| `CHECKLIST.md` | The printable checklist. |
| `METHOD.md` | How to run the scorecard as an anonymous survey, including small-group suppression (groups under 5 are not reported) and the self-selected sample caveat. |
| `tools/make_qr.py`, `tools/make_card.py` | Make a QR code and a printable card for a talk or workshop. |
| `responses_example.txt` | Synthetic example codes for trying the aggregator. Delete before collecting real data. |

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
