# Licenses

| What | License |
|---|---|
| Code in this repository (`secondchance/`, `scripts/`, `tests/`) | Apache License 2.0 ([LICENSE](../LICENSE)) |
| Annotations and results (`checkpoints/` metadata, evaluation records and fixability evidence, `conditions/`, `results/`, the Hugging Face dataset) | CC BY 4.0 |
| Task content from τ²-bench (tasks, policies, tool outputs and database states in the τ²-bench, retail and airline checkpoint histories and states) | MIT License, © 2025 Sierra Research (https://github.com/sierra-research/tau2-bench) |
| Task content from BFCL (scripted user turns, function documentation, tool outputs in the BFCL checkpoint histories) | Apache License 2.0 (https://github.com/ShishirPatil/gorilla) |
| AppWorld | not redistributed (below) |

## AppWorld

AppWorld (https://github.com/StonyBrookNLP/appworld, Apache License 2.0) releases its task-specific portion (API documentation and
implementation, task solutions, evaluation tests, task data) in encrypted bundles "under the Apache 2.0 license with an additional
requirement that any of its public redistribution (or of its derivatives) should be done in an encrypted format", and asks users not to
post data extracted or derived from those bundles in plain text. The histories, states, correction and protection targets, corrective
routes, certificates and the localized and plan-assisted assistance texts of the 54 AppWorld checkpoints derive from that portion, so they
are not included. The results and labels of the AppWorld checkpoints (outcomes, counts, error kinds, fixability, AppWorld task ids) are
included, and every table of the paper reproduces from the shipped files.

## τ²-bench and BFCL

Neither license restricts redistribution beyond keeping the copyright and license notices, which this page and the `source` field of
every checkpoint carry. The τ²-bench name `tau2` on PyPI belongs to an unrelated package; install τ²-bench with `secondchance setup tau2`.

## Model outputs

The histories and results contain outputs of the evaluated models and of the simulated user (GPT-4.1). They are released for research use
as part of the benchmark.
