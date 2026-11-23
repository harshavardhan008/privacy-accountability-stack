# Privacy Accountability Stack

Privacy accountability for enterprise AI, from the data an AI learns from to the actions an AI agent takes.

Identity tells you who the agent is. Security tells you what could go wrong. Privacy accountability tells you why the agent may touch this person's data, and whether you can prove it later.

## The stack

| Layer | Question it answers | Where it is covered |
|---|---|---|
| 0. Synthetic data | Can we build and test without real personal data? | GICITE 2026 paper, book |
| 1. Lineage | Where did this data come from and where did it go? | GICITE 2026 paper; runtime in `agent-action-record` |
| 2. Consent and minimization | Was this use allowed, and was only the needed data used? | GICITE 2026 paper; runtime in `agent-action-record` |
| 3. Audit | Can we prove what happened? | GICITE 2026 paper; runtime in `agent-action-record` |
| 4. Regulatory alignment | Does this map to the rules that apply? | GICITE 2026 and CICN 2026 papers |

The first publication defined the stack for training-time data. This repository extends it to runtime, where AI agents act instead of only answer.

## What is in this repository

| Module | What it is |
|---|---|
| [`agent-action-record/`](agent-action-record/) | Runtime module. A reference implementation of the Purpose Pass, a purpose gateway, Action Lineage, the Action Record, a tamper-evident ledger, and a graduation ladder. Python, standard library only, 42 tests. |
| [`agent-privacy-clinic/`](agent-privacy-clinic/) | Checkup and exam. A five-check readiness scorecard with a survey method, and the Clinic Exam, which runs leak attacks against an unguarded agent, a text-scanner agent, and agents behind the gateway, with confidence intervals. |
| [`docs/`](docs/) | The stack explained, and the publication list. |

## Try it in the browser

* **Live demo:** https://harshavardhan008.github.io/privacy-accountability-stack/demo/ runs the real code in your browser on synthetic data.
* **Agent Privacy Clinic checkup:** https://harshavardhan008.github.io/privacy-accountability-stack/agent-privacy-clinic/
* **Clinic Exam:** https://harshavardhan008.github.io/privacy-accountability-stack/agent-privacy-clinic/exam/

## Quick start

```bash
cd agent-action-record
pip install -e ".[dev]"
pytest -q
python examples/loyalty_points_demo.py
```

The demo runs a support agent that fixes missing loyalty points. It shows the purpose gateway releasing only the fields the purpose needs, denying a purpose-widening request, and writing an Action Record for every step.

## Related work

Red-team tools such as [finleak](https://github.com/vasukoduri/finleak) test from outside whether a model leaks data. This repository controls from inside what an agent may access, for what purpose, and records it. The Clinic Exam borrows the idea of measuring leakage with attack probes and confidence intervals, and applies it to those controls.

## Evidence and limits

The evaluation uses 200 synthetic customers and constructed scenarios. It shows the mechanisms work as designed. It does not measure how common these failures are in real deployments. The readiness scorecard exists to start collecting that evidence, anonymously and with small-group suppression. Limits and known bypasses are documented in `agent-action-record/docs/ARCHITECTURE.md`.

## Publications

See [`docs/PUBLICATIONS.md`](docs/PUBLICATIONS.md).

## Cite

Use `CITATION.cff` (the GitHub "Cite this repository" button).

## Contributing

Critiques are the most useful contribution. See [`CONTRIBUTING.md`](CONTRIBUTING.md). All data in issues, tests, and examples must be synthetic.

## License

MIT. See `LICENSE`.

Maintainer: Harshavardhan Peddireddy, Senior Member, IEEE.
