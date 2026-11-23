"""BFCL v4 multi-turn checkpoints: backends, restore and replay verification (ported unchanged from the frozen evaluation's adapter).

Tool calls execute as structured method calls on per-run backend instances (no eval of model-produced strings, no module globals).
A checkpoint is restored as fresh instances from the task's initial_config plus a replay of the calls executed in the history; the replayed
outputs must equal the recorded ones and the state hash must equal the recorded hash. The per-turn state check (public attributes) is the
official BFCL one. Needs `pip install secondchance[bfcl]` (bfcl_eval at the pinned commit)."""
from __future__ import annotations

import copy
import hashlib
import importlib
import inspect
import json
from pathlib import Path

import bfcl_eval
from bfcl_eval.constants.executable_backend_config import CLASS_FILE_PATH_MAPPING, STATELESS_CLASSES

DATA = Path(bfcl_eval.__file__).resolve().parent / "data"
CATEGORIES = ["multi_turn_base", "multi_turn_miss_param", "multi_turn_miss_func", "multi_turn_long_context"]
DOC_FILE = {"GorillaFileSystem": "gorilla_file_system", "MathAPI": "math_api", "MessageAPI": "message_api", "TwitterAPI": "posting_api",
            "TicketAPI": "ticket_api", "TradingBot": "trading_bot", "TravelAPI": "travel_booking", "VehicleControlAPI": "vehicle_control"}


def load_entries(category):
    q = [json.loads(l) for l in (DATA / f"BFCL_v4_{category}.json").read_text().splitlines()]
    a = {json.loads(l)["id"]: json.loads(l)["ground_truth"] for l in (DATA / "possible_answer" / f"BFCL_v4_{category}.json").read_text().splitlines()}
    for e in q:
        e["ground_truth"] = a[e["id"]]
        e["category"] = category
    return q


def _schema(p):
    if isinstance(p, dict):
        p = {k: _schema(v) for k, v in p.items()}
        if p.get("type") == "dict":
            p["type"] = "object"
        if p.get("type") == "float":
            p["type"] = "number"
        if p.get("type") == "tuple":
            p["type"] = "array"
        if p.get("type") == "any":
            p.pop("type")
        return p
    if isinstance(p, list):
        return [_schema(x) for x in p]
    return p


def tools_for(entry, turn_index):
    """OpenAI tool specs available at a turn: functions of the involved classes, minus excluded ones and minus functions withheld until a
    later turn (miss_func); BFCL makes withheld functions available from their turn onward."""
    withheld = {f for t, fs in (entry.get("missed_function") or {}).items() if int(t) > turn_index for f in fs}
    excluded = set(entry.get("excluded_function") or [])
    out = []
    for cls in entry["involved_classes"]:
        for l in (DATA / "multi_turn_func_doc" / f"{DOC_FILE[cls]}.json").read_text().splitlines():
            d = json.loads(l)
            if d["name"] in withheld or d["name"] in excluded:
                continue
            out.append({"type": "function", "function": {"name": d["name"], "description": d["description"], "parameters": _schema(d["parameters"])}})
    return out


class Backend:
    """Per-run backend instances (isolated; no globals)."""

    def __init__(self, entry):
        self.entry = entry
        self.instances, self.methods = {}, {}
        for cls in entry["involved_classes"]:
            mod = importlib.import_module(CLASS_FILE_PATH_MAPPING[cls])
            inst = getattr(mod, cls)()
            if cls not in STATELESS_CLASSES:
                inst._load_scenario(copy.deepcopy(entry["initial_config"].get(cls, {})), long_context=entry["category"] == "multi_turn_long_context")
            self.instances[cls] = inst
            for name, meth in inspect.getmembers(inst, predicate=inspect.ismethod):
                if not name.startswith("_"):
                    self.methods[name] = meth
        self.executed = []

    def call(self, name, arguments):
        if name not in self.methods:
            out = f"Error during execution: function {name} not found"
        else:
            try:
                r = self.methods[name](**(arguments or {}))
                out = r if isinstance(r, str) else (json.dumps(r) if isinstance(r, dict) else str(r))
            except Exception as e:  # noqa: BLE001
                out = f"Error during execution: {e}"
        self.executed.append({"name": name, "arguments": arguments, "output": out})
        return out

    def state(self):
        s = {}
        for cls, inst in self.instances.items():
            s[cls] = {k: _jsonable(v) for k, v in vars(inst).items() if not k.startswith("_")}
        return s

    def state_hash(self):
        return hashlib.sha256(canon(self.state()).encode()).hexdigest()


def _jsonable(v, _path=None):
    """JSON-safe deep copy of public state; back-references (e.g. a directory's parent) become '<cycle>' instead of recursing."""
    _path = _path or set()
    try:
        json.dumps(v); return copy.deepcopy(v)
    except (TypeError, ValueError, RecursionError):
        pass
    if id(v) in _path:
        return "<cycle>"
    p2 = _path | {id(v)}
    if isinstance(v, dict):
        return {str(k): _jsonable(x, p2) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_jsonable(x, p2) for x in v]
    if hasattr(v, "__dict__"):
        return {"__class__": type(v).__name__, **{k: _jsonable(x, p2) for k, x in vars(v).items() if not k.startswith("_") and k != "parent"}}
    return repr(v)


def _strkeys(v):
    if isinstance(v, dict):
        return {str(k): _strkeys(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_strkeys(x) for x in v]
    return v


def canon(v):
    """Canonical JSON (keys stringified, sorted) used for hashing and state comparison."""
    return json.dumps(_strkeys(v), sort_keys=True, default=str)


def parse_gt_call(s):
    """'mv(source='a', destination='b')' -> ('mv', {...}) using Python's parser (literals only; no eval of names)."""
    import ast
    node = ast.parse(s.strip(), mode="eval").body
    assert isinstance(node, ast.Call)
    name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
    args = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords}
    if node.args:  # positional (e.g. sort('final_report.pdf')): map to the doc's parameter order
        args["__positional__"] = [ast.literal_eval(a) for a in node.args]
    return name, args


def _bind_positional(backend, name, args):
    if "__positional__" not in args:
        return args
    pos = args.pop("__positional__")
    params = [p for p in inspect.signature(backend.methods[name]).parameters]
    return {**dict(zip(params, pos)), **args}


def reference_states(entry):
    """Per-turn reference states from replaying the ground-truth calls (the official state-check target)."""
    b = Backend(entry); states = []
    for turn in entry["ground_truth"]:
        for c in turn:
            n, a = parse_gt_call(c)
            b.call(n, _bind_positional(b, n, a))
        states.append(b.state())
    return states


def restore(entry, executed_calls):
    """Checkpoint restoration: fresh backends + replay of the executed calls; verified by output equality. Returns (backend, ok, mismatches)."""
    b = Backend(entry); mism = []
    for i, c in enumerate(executed_calls):
        out = b.call(c["name"], c["arguments"])
        if out != c["output"]:
            mism.append(i)
    return b, not mism, mism


def turn_state_check(backend, ref_state):
    """Official-style state check: every public attribute equal to the reference for the involved classes."""
    s = backend.state(); diffs = []
    for cls, attrs in ref_state.items():
        for k, v in attrs.items():
            if canon(s.get(cls, {}).get(k)) != canon(v):
                diffs.append(f"{cls}.{k}")
    return not diffs, diffs


MAX_STEPS_PER_TURN = 20
SYSTEM = ("You are an assistant that completes the user's requests by calling the available functions. Call functions when needed; "
          "when a request lacks information you need, ask the user instead of guessing. Reply in text when the turn's request is done.")


def entry_for(task):
    cat = next(c for c in CATEGORIES if task.startswith(c + "_") and task[len(c) + 1:].isdigit())
    return next(e for e in load_entries(cat) if e["id"] == task)


def restore_checkpoint(ck):
    """(backend at the checkpoint, task entry, report). A continuation must not start unless report['ok']."""
    entry = entry_for(ck.restore["task"])
    backend, ok, mism = restore(entry, [{"name": c["name"], "arguments": c["arguments"], "output": c["output"]} for c in ck.restore["replay"]])
    h = backend.state_hash()
    report = {"checkpoint": ck.id, "replayed_calls": len(ck.restore["replay"]), "mismatched_outputs": mism, "state_hash": h,
              "state_hash_matches": h == ck.restore["state_hash"]}
    report["ok"] = ok and report["state_hash_matches"]
    return backend, entry, report
