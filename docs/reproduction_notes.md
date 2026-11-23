# Notes on reproducing the paper's tables

`python scripts/verify.py` recomputes every table and Figure 2 from `results/` and checks each printed number against the paper. Three
details of the printed tables are reproduced as printed:

1. **Rounding in Table 11.** Table 11 rounds exact halves up (`int(100 k / n + 0.5)`); the other rate tables use Python's formatting
   of `k / n` to two decimals. The only visible case is Qwen3-4B's "Chg." in Table 11: 9 of 72 runs = .125, printed as .13.
2. **AppWorld agent calls in Table 11.** For the 90 AppWorld runs that were continued to the source episodes' block limit, the "Run" and
   "Rec." columns of Table 11 count the agent calls before that continuation (`agent_calls_before_extension`), while Table 17 and the
   `agent_calls` field count the whole run.
3. **Retail and airline intervals in Table 14.** The bootstrap for the retail and airline rows resamples checkpoints (each its own
   cluster) rather than source tasks.

Bootstrap intervals use 2,000 resamples with `random.Random(0)`; the clusters are sorted before resampling, so the intervals are exactly
reproducible. Table 14's three-sample rows draw the comparisons N-U, L-U, PA-U and PA-L (not printed) from one generator per environment.
