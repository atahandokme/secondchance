# Pins

Everything the frozen evaluation depended on. The same values are in `secondchance/__init__.py` (`PINS`).

## Environments

| Environment | Source | Pin |
|---|---|---|
| τ²-bench (telecom, banking, retail, airline) | https://github.com/sierra-research/tau2-bench | commit `5bfa7e37b36656b37dc6d022156be6563c1007f3` (package version 1.0.1); `secondchance setup tau2` installs it and its `data/` folder |
| BFCL v4 multi-turn | https://github.com/ShishirPatil/gorilla (`berkeley-function-call-leaderboard`) | commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`; identical to PyPI `bfcl-eval==2026.3.23` (all 183 files) |
| AppWorld | https://github.com/StonyBrookNLP/appworld | commit `42b5bcf3cd334fee33f0c37c02070a9f5807add5` (checkpoint contents not distributed, [licenses.md](licenses.md)) |

## Libraries

| Library | Version | Why it matters |
|---|---|---|
| Python | 3.12 (tau2-bench requires >=3.12,<3.14) | |
| pydantic | 2.13.5 | tau2-bench tool error messages contain pydantic's version; replay verification compares them exactly |
| litellm | 1.82.6 | tau2-bench's agent and user-simulator calls |
| mpmath | 1.3.0 | BFCL MathAPI backend |
| vLLM | 0.11.2 and 0.32.0 (per model, below) | serving the open-weight models |

## Evaluated open-weight models

Served with vLLM's OpenAI-compatible server, 32,768-token context, at most 4,096 output tokens per call. Main study: greedy decoding
(temperature 0, seed 0). Repeated runs: temperature 0.7, three samples.

| Model | Checkpoint | Revision | vLLM | Tool parser | Context | GPUs | Request |
|---|---|---|---|---|---|---|---|
| Qwen3-4B | `Qwen/Qwen3-4B-Instruct-2507` | `cdbee75f17c01a7cc42f958dc650907174af0554` | 0.11.2 | `hermes` | 32,768 | 1 | -- |
| Llama-3.1-8B | `meta-llama/Llama-3.1-8B-Instruct` | `0e9e39f249a16976918f6564b8830bc894c89659` | 0.11.2 | `llama3_json` | 32,768 | 1 | -- |
| gpt-oss-20b | `openai/gpt-oss-20b` | `6cee5e81ee83917806bbde320786a8fb61efebee` | 0.32.0 | `openai` | 32,768 | 1 | {"reasoning_effort": "low"} |
| Mistral-Small-3.2 | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` | `95a6d26c4bfb886c58daf9d3f7332c857cb27b43` | 0.11.2 | `mistral` | 32,768 | 2 | -- |
| Qwen3-32B | `Qwen/Qwen3-32B` | `9216db5781bf21249d130ec9da846c4624c16137` | 0.11.2 | `hermes` | 32,768 | 2 | {"chat_template_kwargs": {"enable_thinking": false}} |
| Qwen3.5-35B-A3B | `Qwen/Qwen3.5-35B-A3B` | `59d61f3ce65a6d9863b86d2e96597125219dc754` | 0.32.0 | `qwen3_coder` | 32,768 | 2 | -- |
| Gemma-4-31B | `google/gemma-4-31b-it` | `842da3794eaa0b77d5f08bae87a17459d91ff475` | 0.32.0 | `gemma4` | 32,768 | 2 | -- |
| Llama-3.3-70B | `meta-llama/Llama-3.3-70B-Instruct` | `6f6073b423013f6a7d4d9f39144961bfbfbc386b` | 0.11.2 | `llama3_json` | 32,768 | 4 | -- |
| gpt-oss-120b | `openai/gpt-oss-120b` | `b5c939de8f754692c1647ca79fbf85e8c1e70f8a` | 0.32.0 | `openai` | 32,768 | 2 | {"reasoning_effort": "low"} |
| Qwen3-235B | `Qwen/Qwen3-235B-A22B-GPTQ-Int4` | `dff138951f3898772fc0d795a4b5b30f417577f4` | 0.11.2 | `hermes` | 32,768 | 4 | {"chat_template_kwargs": {"enable_thinking": false}} |

## Hosted models

| Model | API model id | Interface | Settings |
|---|---|---|---|
| GPT-5.4-mini | `gpt-5.4-mini-2026-03-17` | Chat Completions | reasoning disabled, temperature 0.7, seeds 1 to 3 (provider seeding is best effort); the main study uses seed 1 |
| GPT-5.5 | `gpt-5.5-2026-04-23` | Responses API | reasoning effort low, provider-default sampling (temperature and seed not accepted); three-sample comparison only |
| GPT-6.1-sol | `gpt-6.1-sol` (an alias, not a dated snapshot) | Responses API | reasoning effort low, provider-default sampling; the main study uses the first of three samples |

## Simulated user and judge

| Role | Model | Settings |
|---|---|---|
| τ²-bench simulated user | `gpt-4.1-2025-04-14` | temperature 0; tau2-bench's own user simulator and prompts |
| Semantic review judge (stage 2) and the acknowledged measure | `Qwen/Qwen3-235B-A22B-GPTQ-Int4`, revision `dff138951f3898772fc0d795a4b5b30f417577f4`, vLLM 0.11.2 | temperature 0, seed 0, at most 3,000 output tokens, thinking disabled |

## Budgets

| Environment | Continuation budget |
|---|---|
| τ²-bench, retail, airline | the episode's 200 orchestrator steps, counted from the start of the episode (a continuation gets 200 minus the steps of its history); at most 10 tool errors |
| BFCL | 20 model steps per scripted turn |
| AppWorld | the source episodes' 50-block limit, counted from the start, and at least 15 blocks |
