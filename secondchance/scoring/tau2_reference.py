"""tau2-bench environment construction and reference (gold) actions."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401


def _env(domain, task):
    from tau2.registry import registry

    env = registry.get_env_constructor(domain)()
    init = task.initial_state
    env.set_state(init.initialization_data if init else None, init.initialization_actions if init else None, [])
    return env


def _apply_gold(env, task, skip=frozenset()):
    from tau2.data_model.message import ToolCall

    errs = []
    for i, a in enumerate(task.evaluation_criteria.actions or []):
        if i in skip:
            continue
        r = env.get_response(ToolCall(id=a.action_id or "gold", name=a.name, arguments=a.arguments,
                                      requestor=a.requestor))
        if r.error:
            errs.append(f"{a.name}: {str(r.content)[:120]}")
    return errs
