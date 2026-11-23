# Baselines

The four assistance conditions are the benchmark's built-in baselines. Each adds information to the previous one; all four are run on
every checkpoint.

| Condition | What the agent receives in addition to the restored history |
|---|---|
| U (unaided) | Nothing: the agent continues from the recorded history. |
| N (notified) | "Note: an earlier action taken in this conversation was a mistake." |
| L (localized) | The notice plus the erroneous action (the call, its arguments and its position in the conversation). |
| PA (plan-assisted) | A description of the error and checkpoint-specific repair guidance: what the action changed, a verified way to undo it where one exists, established limits where the target is unreachable, and when to involve the user. |

The texts are in `conditions/<checkpoint>.json` (τ²-bench, BFCL, retail, airline), each with its SHA-256.

`main_study.jsonl` (built by `make_baselines.py` from `results/main_study.jsonl`) gives, for each of the 12 models of the paper, each
environment and condition: the number of runs and the counts and rates of correction, task success and complete recovery, on all
checkpoints and on the checkpoints with a demonstrated fix. A new method (a model, a prompt, a recovery procedure) evaluated with
`secondchance run` and `secondchance score` on the same checkpoints and conditions compares directly against these rows.
