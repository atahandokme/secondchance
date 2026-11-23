"""SecondChance: an error checkpoint dataset and evaluation harness for error recovery in AI agents."""
__version__ = "1.0.0"

# Everything the frozen evaluation depends on (docs/pins.md lists the same values).
PINS = {
    "tau2_bench": {"repo": "https://github.com/sierra-research/tau2-bench", "commit": "5bfa7e37b36656b37dc6d022156be6563c1007f3"},
    "bfcl": {"repo": "https://github.com/ShishirPatil/gorilla", "commit": "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8",
             "subdirectory": "berkeley-function-call-leaderboard"},
    "appworld": {"repo": "https://github.com/StonyBrookNLP/appworld", "commit": "42b5bcf3cd334fee33f0c37c02070a9f5807add5"},
    "judge_model": "Qwen/Qwen3-235B-A22B-GPTQ-Int4",
    "judge_temperature": 0.0,
    "user_simulator_model": "gpt-4.1-2025-04-14",
    "vllm": "0.11.2",
    "python": ">=3.12,<3.14",
}
