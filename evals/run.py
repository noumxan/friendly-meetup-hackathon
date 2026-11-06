"""Run every test case through the agent, score it, and save a scorecard.

  uv run python -m evals.run --label baseline
  uv run python -m evals.run --only late-refund    # one case
  uv run python -m evals.run --no-judge            # checks only (faster)
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from agent.agent import run_agent
from evals.checks import CHECKS
from evals.judge import judge

ROOT = Path(__file__).parent.parent
console = Console()


def icon(passed: bool | None) -> str:
    return {True: "✅", False: "❌", None: "➖"}[passed]


def overall_passed(checks: list[dict], verdict: dict | None, result: dict) -> bool | None:
    """A case passes only when every check that ran, and the judge, passed.

    An agent error fails the case. A judge error is a failed judge, not a skip.
    Nothing scored at all stays unscored (None).
    """
    if "error" in result:
        return False
    outcomes = [c["passed"] for c in checks]
    if verdict is not None:
        outcomes.append(verdict.get("passed"))
    scored = [o for o in outcomes if o is not None]
    if not scored:
        return None
    return all(scored)


def judge_label(verdict: dict | None) -> str:
    if not verdict:
        return "-"
    if verdict.get("error") or verdict.get("score") is None:
        return "ERR"
    return f"{verdict['score']}/5"


def evaluate(case: dict, use_judge: bool) -> dict:
    try:
        result = run_agent(case["input"])
    except Exception as e:
        result = {"answer": "", "tool_calls": [], "latency_s": 0, "tokens": 0, "error": str(e)}
        console.print(f"[red]Agent error on {case['id']}: {e}[/red]")

    checks = []
    for check in case.get("checks", []):
        fn = CHECKS.get(check["type"])
        if fn is None:
            console.print(f"[yellow]Unknown check type '{check['type']}' in {case['id']}[/yellow]")
        try:
            passed = fn(result, check.get("value")) if fn else None
        except Exception as e:
            console.print(f"[yellow]Check {check.get('type')} crashed on {case['id']}: {e}[/yellow]")
            passed = False
        checks.append({**check, "passed": passed})

    verdict = judge(case, result) if use_judge else None
    if verdict and verdict.get("error"):
        console.print(f"[red]Judge error on {case['id']}: {verdict['reason']}[/red]")

    return {
        "case": case,
        "result": result,
        "checks": checks,
        "judge": verdict,
        "passed": overall_passed(checks, verdict, result),
    }


def print_scorecard(rows: list[dict]) -> None:
    table = Table(title="Scorecard")
    for column in ["Case", "Pass", "Checks", "Judge", "Tools used", "Secs"]:
        table.add_column(column)
    for row in rows:
        verdict = row["judge"]
        table.add_row(
            row["case"]["id"],
            icon(row["passed"]),
            " ".join(icon(c["passed"]) for c in row["checks"]) or "-",
            judge_label(verdict),
            ", ".join(t["name"] for t in row["result"]["tool_calls"]) or "-",
            str(row["result"]["latency_s"]),
        )
    console.print(table)

    scored = [r for r in rows if r["passed"] is not None]
    passes = sum(r["passed"] for r in scored)
    by_tag = defaultdict(list)
    for r in scored:
        for tag in r["case"].get("tags", []):
            by_tag[tag].append(r["passed"])

    console.print(f"[bold]Pass rate: {passes}/{len(scored)}[/bold]  (not scored: {len(rows) - len(scored)})")
    failed = [r["case"]["id"] for r in rows if r["passed"] is False]
    if failed:
        console.print("Failed: " + ", ".join(failed))
    console.print("By tag: " + ", ".join(f"{t} {sum(v)}/{len(v)}" for t, v in sorted(by_tag.items())))
    console.print(
        f"Avg latency: {sum(r['result']['latency_s'] for r in rows) / len(rows):.1f}s  "
        f"Total tokens: {sum(r['result']['tokens'] for r in rows)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="run", help="name for this run, e.g. baseline")
    parser.add_argument("--cases", default=ROOT / "evals" / "cases.jsonl", type=Path)
    parser.add_argument("--only", help="run a single case by id")
    parser.add_argument("--no-judge", action="store_true")
    args = parser.parse_args()

    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]

    rows = []
    for case in cases:
        with console.status(f"Running {case['id']}..."):
            rows.append(evaluate(case, use_judge=not args.no_judge))

    print_scorecard(rows)

    out = ROOT / "results" / f"{datetime.now():%Y%m%d-%H%M%S}-{args.label}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    console.print(f"Saved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
