# Contributing

This is an early reference implementation. The most useful contributions are critiques.

**Ways to help**

* **Break it.** Find an agent behavior the gateway should catch and does not. Open an issue with a minimal scenario.
* **Challenge the record.** Is a field missing, or one not worth the cost? Open an issue labeled `standards-feedback`.
* **Share an adoption story.** What did you change when you tried the checklist or the ladder? Short write-ups are welcome, with permission to quote you.
* **Add integrations.** Adapters for agent frameworks and tool protocols, kept out of the core package so it stays dependency-free.

**Ground rules**

* No real personal data in issues, tests, examples, or logs. Everything must be synthetic.
* Keep the core readable. Plain dataclasses, no required dependencies.
* Every behavior change needs a test. Run `pytest` (inside `agent-action-record/`) before opening a pull request.
* Document limits honestly. If a control can be bypassed, say how in `docs/ARCHITECTURE.md`.

**Security issues** in the reference code: open an issue with the label `security`, or contact the maintainer privately if it involves a real deployment.
