#!/usr/bin/env python3
"""
LLM-as-judge eval runner for GroundWork stress-test outputs.

Examples:
  python evals/run_eval.py --list
  python evals/run_eval.py --scenario experiment_exec_kill_pm
  python evals/run_eval.py --all
  python evals/run_eval.py --scenario move_fast_pm_design_gate --synthesis fallback
  python evals/run_eval.py --scenario experiment_exec_kill_pm --show-judge-prompt
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.judge.client import run_judge
from evals.judge.prompts import build_judge_user_prompt
from evals.judge.rubric import DIMENSIONS, PASS_DIMENSION_MIN, PASS_OVERALL_MIN
from evals.judge.schema import ScenarioResult
from reality_check.config import settings
from reality_check.engine.loader import aspiration_by_id
from reality_check.engine.retrieval import retrieve
from reality_check.engine.synthesis import synthesize_with_meta


FIXTURES_PATH = Path(__file__).parent / "fixtures" / "scenarios.json"
RESULTS_DIR = Path(__file__).parent / "results"


def load_scenarios() -> list[dict]:
    data = json.loads(FIXTURES_PATH.read_text())
    return data["scenarios"]


def _selection_label(scenario: dict) -> str:
    if scenario.get("aspiration_id"):
        asp = aspiration_by_id().get(scenario["aspiration_id"])
        return asp["label"] if asp else scenario["aspiration_id"]
    return scenario.get("philosophy_id", "custom")


async def generate_output(scenario: dict, *, force_fallback: bool) -> tuple[dict, str, float]:
    """Run retrieval + synthesis; return (response dict, path, latency)."""
    org = scenario["org_profile"]
    aspiration = None
    if scenario.get("aspiration_id"):
        aspiration = aspiration_by_id().get(scenario["aspiration_id"])

    pid = scenario.get("philosophy_id")
    if aspiration and not pid:
        pid = aspiration["philosophy_id"]

    bundle = retrieve(
        pid,
        org,
        aspiration=aspiration,
    )

    old_skip = settings.reality_check_skip_llm
    if force_fallback:
        settings.reality_check_skip_llm = True

    started = time.perf_counter()
    try:
        response, path = await synthesize_with_meta(bundle)
    finally:
        settings.reality_check_skip_llm = old_skip

    latency = time.perf_counter() - started
    return response.model_dump(), path, latency


def _passes_thresholds(verdict) -> bool:
    if verdict.overall_score < PASS_OVERALL_MIN:
        return False
    return all(d.score >= PASS_DIMENSION_MIN for d in verdict.dimensions)


def _print_scenario_result(result: ScenarioResult) -> None:
    v = result.verdict
    passed = _passes_thresholds(v)
    status = "PASS" if passed else "FAIL"
    print()
    print("=" * 72)
    print(f"[{status}] {result.scenario_id}  |  synthesis: {result.synthesis_path}  |  {result.latency_seconds:.1f}s")
    print(f"Description: {result.scenario_description}")
    print("-" * 72)
    print(f"HEADLINE: {result.headline}")
    if result.gap_notice:
        print(f"GAP: {result.gap_notice}")
    print(f"\nJudge overall: {v.overall_score:.1f}/5  |  judge pass: {v.pass_recommendation}")
    print(f"Summary: {v.summary}")
    if v.critical_issues:
        print("Critical issues:")
        for issue in v.critical_issues:
            print(f"  - {issue}")
    print("\nDimensions:")
    for d in v.dimensions:
        flag = "!" if d.score < PASS_DIMENSION_MIN else " "
        print(f"  {flag} {d.dimension:22} {d.score}/5  — {d.evidence[:90]}")
        if d.score < 5:
            print(f"      → {d.improvement[:100]}")
    print("=" * 72)


def _print_summary(results: list[ScenarioResult]) -> None:
    print("\n" + "#" * 72)
    print("SUMMARY")
    print("#" * 72)
    for r in results:
        v = r.verdict
        ok = _passes_thresholds(v)
        print(
            f"  {'✓' if ok else '✗'} {r.scenario_id:32}  "
            f"path={r.synthesis_path:18}  overall={v.overall_score:.1f}  "
            f"min_dim={min(d.score for d in v.dimensions)}"
        )
    n_pass = sum(1 for r in results if _passes_thresholds(r.verdict))
    print(f"\nPassed {n_pass}/{len(results)} against thresholds "
          f"(overall≥{PASS_OVERALL_MIN}, each dimension≥{PASS_DIMENSION_MIN})")


def _write_results_file(
    results: list[ScenarioResult],
    *,
    synthesis_mode: str,
    judge_model: str | None,
    output_path: str | None,
) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if output_path:
        out_path = Path(output_path)
        if not out_path.is_absolute():
            out_path = (ROOT / out_path).resolve()
    else:
        out_path = RESULTS_DIR / f"judge_{stamp}.json"

    payload = {
        "generated_at": stamp,
        "synthesis_mode": synthesis_mode,
        "judge_model": judge_model or settings.openai_model,
        "thresholds": {"overall_min": PASS_OVERALL_MIN, "dimension_min": PASS_DIMENSION_MIN},
        "results": [r.model_dump() for r in results],
    }
    text = json.dumps(payload, indent=2)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    (RESULTS_DIR / "latest.json").write_text(text)
    return out_path


async def run_one(
    scenario: dict,
    *,
    force_fallback: bool,
    judge_model: str | None,
    show_judge_prompt: bool,
) -> ScenarioResult:
    output, path, latency = await generate_output(scenario, force_fallback=force_fallback)

    if show_judge_prompt:
        print("\n--- JUDGE PROMPT (user message) ---\n")
        print(build_judge_user_prompt(scenario, output, path))
        print("\n--- END PROMPT ---\n")

    verdict = run_judge(scenario, output, path, model=judge_model)

    snap = {**output, "aspiration_id": scenario.get("aspiration_id"), "philosophy_id": scenario.get("philosophy_id")}
    return ScenarioResult(
        scenario_id=scenario["id"],
        scenario_description=scenario.get("description", ""),
        synthesis_path=path,
        latency_seconds=round(latency, 2),
        headline=output.get("headline", ""),
        gap_notice=output.get("gap_notice"),
        verdict=verdict,
        output_snapshot=snap,
    )


async def async_main(args: argparse.Namespace) -> int:
    scenarios = load_scenarios()
    by_id = {s["id"]: s for s in scenarios}

    if args.list:
        print("Scenarios:")
        for s in scenarios:
            print(f"  - {s['id']}: {s.get('description', '')[:70]}")
        print(f"\nRubric dimensions: {', '.join(d['id'] for d in DIMENSIONS)}")
        return 0

    if args.scenario:
        selected = [by_id[args.scenario]]
    elif args.all:
        selected = scenarios
    else:
        print("Specify --scenario <id> or --all (or --list)", file=sys.stderr)
        return 1

    force_fallback = args.synthesis == "fallback"
    results: list[ScenarioResult] = []
    save_payload = args.save

    try:
        for scenario in selected:
            print(f"\nRunning {scenario['id']} ({args.synthesis})…")
            try:
                result = await run_one(
                    scenario,
                    force_fallback=force_fallback,
                    judge_model=args.judge_model,
                    show_judge_prompt=args.show_judge_prompt and len(selected) == 1,
                )
            except Exception as exc:
                print(f"\nERROR on {scenario['id']}: {exc}", file=sys.stderr)
                if not save_payload:
                    raise
                continue
            results.append(result)
            _print_scenario_result(result)

        if results:
            _print_summary(results)
    finally:
        if save_payload and results:
            out_path = _write_results_file(
                results,
                synthesis_mode=args.synthesis,
                judge_model=args.judge_model,
                output_path=args.output,
            )
            latest = RESULTS_DIR / "latest.json"
            print(f"\nSaved report:")
            print(f"  {out_path.resolve()}")
            print(f"  {latest.resolve()}  (same content — open this in the editor)")

    if not results:
        return 1

    return 0 if all(_passes_thresholds(r.verdict) for r in results) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="GroundWork LLM-as-judge eval runner")
    parser.add_argument("--list", action="store_true", help="List fixture scenarios")
    parser.add_argument("--scenario", type=str, help="Run one scenario by id")
    parser.add_argument("--all", action="store_true", help="Run all fixture scenarios")
    parser.add_argument(
        "--synthesis",
        choices=("llm", "fallback"),
        default="llm",
        help="Generate output via OpenAI (llm) or corpus fallback only",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default=None,
        help="OpenAI model for judging (default: OPENAI_MODEL from .env)",
    )
    parser.add_argument(
        "--show-judge-prompt",
        action="store_true",
        help="Print the judge user prompt (single scenario only)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Write JSON to evals/results/judge_<timestamp>.json and evals/results/latest.json",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path for the report (also writes latest.json)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(async_main(args)))


if __name__ == "__main__":
    main()
