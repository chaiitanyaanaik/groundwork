# GroundWork LLM-as-judge evals

Learn how **LLM-as-judge** evals work by running this harness against real stress-test outputs.

## What this does

For each **scenario** (fixed user + org + calibration):

1. **Generate** a stress-test response (GroundWork synthesis — LLM or fallback).
2. **Judge** that response with a separate LLM call using a rubric.
3. **Print** per-dimension scores, evidence, and a pass/fail summary.

You pay for **two** OpenAI calls per scenario (synthesis + judge). Use `--synthesis fallback` to skip synthesis cost while iterating on the judge prompt.

## Setup

```bash
source .venv/bin/activate
# .env must have OPENAI_API_KEY
```

## Commands

```bash
# List scenarios
python evals/run_eval.py --list

# One scenario (best for learning)
python evals/run_eval.py --scenario experiment_exec_kill_pm --save

# See exactly what the judge sees
python evals/run_eval.py --scenario experiment_exec_kill_pm --show-judge-prompt

# Corpus-only synthesis (fast, no synthesis LLM cost)
python evals/run_eval.py --scenario move_fast_pm_design_gate --synthesis fallback

# Full suite (5 scenarios × synthesis + judge)
python evals/run_eval.py --all --save
```

Exit code `0` = all scenarios passed **your** thresholds; `1` = at least one failed.

### Saving results

With `--save`, the runner writes:

- `evals/results/latest.json` — always refreshed (visible in the file tree)
- `evals/results/judge_<UTC>.json` — timestamped copy (gitignored)

You should see:

```
Saved report:
  /.../evals/results/judge_20260526T....json
  /.../evals/results/latest.json  (same content — open this in the editor)
```

Optional fixed path: `--output evals/results/my_run.json`

## Rubric (6 dimensions)

| ID | What you're measuring |
|----|------------------------|
| `mismatch_clarity` | Headline = "want X, but Y" in human language |
| `calibration_use` | At least 2 calibration answers reflected |
| `actionability` | Concrete 30-day actions |
| `philosophy_grounding` | Advice fits the card (not wrong playbook) |
| `tone` | Stress-test, not org audit |
| `evidence_hygiene` | Sources OK, no debug text |

Default pass thresholds (in `evals/judge/rubric.py`):

- Overall ≥ **3.8**
- Each dimension ≥ **3**

The judge also returns `pass_recommendation` (stricter: overall ≥ 4, no dimension &lt; 3).

## How to read output

```
[FAIL] experiment_exec_kill_pm  |  synthesis: llm  |  12.3s
HEADLINE: You want to experiment more without chaos, but ...

Judge overall: 3.6/5  |  judge pass: false
Summary: Strong mismatch but playbook language drifts toward ship velocity.

Dimensions:
    mismatch_clarity       4/5  — Headline names exec deprioritization...
  ! philosophy_grounding   2/5  — Start-with bullets mention blast-radius...
      → Replace with experiment log / insight brief language
```

- **`!`** = below dimension threshold (3).
- **evidence** = what the judge saw in the output (learn whether scores are fair).
- **improvement** = one fix — use these to tune prompts/enrichment.

## Learning exercises

1. **Compare paths**  
   Run the same scenario with `--synthesis llm` vs `--synthesis fallback`.  
   Question: Does the judge score fallback higher on grounding because it's more template-consistent?

2. **Break one dimension**  
   Temporarily break enrichment (e.g. wrong playbook).  
   Question: Does `philosophy_grounding` drop before `mismatch_clarity`?

3. **Edit the judge**  
   Change `evals/judge/prompts.py` SYSTEM_PROMPT anchors. Re-run.  
   Question: Do scores move together (rubrics are calibrated) or randomly?

4. **Judge model swap**  
   `--judge-model gpt-4o` vs default mini.  
   Question: Is the judge stricter or more consistent on `calibration_use`?

5. **Add a scenario**  
   Copy a block in `evals/fixtures/scenarios.json` from your own UI session.  
   Question: Which dimension fails for real user inputs?

## Files

```
evals/
  run_eval.py              # CLI entrypoint
  fixtures/scenarios.json  # frozen inputs
  judge/
    rubric.py              # dimensions + thresholds
    prompts.py             # judge system + user template
    schema.py              # JudgeVerdict pydantic model
    client.py              # OpenAI judge call
  results/
    latest.json            # updated every --save (open this in the editor)
    judge_<timestamp>.json # historical runs (gitignored)
```

## Limitations (on purpose)

- Judge can **hallucinate** failures — always read `evidence`.
- Not a replacement for **human** evals before launch.
- Scenarios use **option ids** in fixtures; labels are resolved at synthesis time.
- No automatic regression in CI yet — add `pytest` wrapper later if scores stabilize.

## Next steps

- Add scenarios from production failures.
- Track `evals/results/judge_*.json` over time (compare `overall_score` trends).
- Wire weakest dimension into prompt iteration checklist.
