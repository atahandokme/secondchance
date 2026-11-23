# Error kinds, mechanisms and fixability

Each checkpoint carries one selected error: the earliest state change of a source episode that the mechanical screen flags and the
selection keeps. `error_kind` names the error for reporting; `mechanism` is the screen's own class.

## τ²-bench (38 checkpoints)

| error_kind | mechanism | What happened |
|---|---|---|
| wrong entity | `WRITE_TO_WRONG_ENTITY` | A write to another entity than the one the user meant (for example roaming enabled on another line of the account) |
| wrong value | `WRONG_VALUE_ON_GOAL_FIELD` | A field the task changes was set to a value the reference never takes |
| unrequested change | `UNREQUESTED_WRITE` | A field the task never changes was changed |
| policy-forbidden action | `POLICY_FORBIDDEN_WRITE` | A write the domain policy forbids |

## BFCL multi-turn (37 checkpoints)

| error_kind | mechanism | What happened |
|---|---|---|
| unwanted change elsewhere | `P:unwanted_change_elsewhere` | An attribute the reference never changes was changed |
| wrong entity | `G:wrong_entity` | A task attribute was changed on the wrong entity |
| wrong value | `G:wrong_value` | A task attribute was set to a wrong value |
| wrong value and unwanted change | `G:wrong_value+P:unwanted_change_elsewhere` | Both |

## AppWorld (54 checkpoints; contents not distributed, see [licenses.md](licenses.md))

| error_kind | mechanism (one or more) | What happened to the database |
|---|---|---|
| unwanted record in a task table | `wrong_or_duplicate_write` | A wrong or duplicate row in a table the task writes |
| record removed | `deleted_preexisting_row` | A row that existed before the task was deleted |
| unwanted record elsewhere | `write_to_model_outside_task` | A row added to a table the task does not touch |
| wrong value on a task record | `wrong_value_on_task_row` | A wrong value on a row the task writes |
| unrelated record modified | `modified_preexisting_row_outside_task` | A row outside the task was modified |
| several effects | a combination of the above | |

## Retail and airline (24 supplementary checkpoints)

No error kind is assigned. 9 checkpoints have a field-level effect with a correction target; for the other 15 the error is procedural
(no field-level effect), their fixability is `not_applicable` and correction is not scored.

## Fixability

Fixability is established for each checkpoint before any agent is evaluated, with no model involved.

| `fixability` | Meaning | `fixability_evidence` |
|---|---|---|
| `demonstrated` | A sequence of permitted actions, executed on the restored checkpoint, satisfies the correction target | `AVAILABLE_ROUTE_SCRIPTED` (a scripted route: the inverse of the erroneous call and/or the task's reference actions), `WITNESSED` (retail/airline) |
| `proven_impossible` | The environment's own code shows that no available operation can produce the target | `CERTIFIED_CLOSED:CATALOG_TARGET_UNWRITABLE` (τ²-bench: no tool of the agent or the user can write the target value), `CERTIFIED_CLOSED:INVERSE_CATALOG_RULE` (BFCL: the backends keep an invariant the target violates, such as a counter that only increases or records that are never deleted) |
| `unknown` | Neither was established. This describes the search, not the error: an unknown checkpoint is **not** a negative | `UNKNOWN:NO_WITNESS_FOUND`, `NO_DEMONSTRATED_ROUTE:CUT_TURN_CERTIFICATE_ONLY` (BFCL: a certificate that covers only the checkpoint's own turn, not the end-of-task target) |
| `not_applicable` | Retail/airline only: no field-level effect, so no correction target | `NO_FIELD_LEVEL_EFFECT` |

Each `checkpoints/<id>/checkpoint.json` gives the evidence: the demonstrated routes (what they undo and redo, who can act, whether the
policy allows them and whether the user must cooperate) or the certificate (its proof and the invariants it uses). A demonstrated fix shows
that a correction exists, not that an agent has the information to find it, and a fix for the error does not show that the whole task can
still be completed (`complete_recovery_route`).
