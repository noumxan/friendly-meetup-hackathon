"""Write a single HTML page from saved JSONL scorecards.

  uv run python -m evals.report results/<before>.jsonl results/<after>.jsonl
"""

import html
import json
import sys
from collections import defaultdict
from pathlib import Path


def load(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def rate(rows: list[dict]) -> tuple[int, int]:
    scored = [row for row in rows if row["passed"] is not None]
    return sum(bool(row["passed"]) for row in scored), len(scored)


def by_tag(rows: list[dict]) -> dict[str, tuple[int, int]]:
    groups: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        if row["passed"] is None:
            continue
        for tag in row["case"].get("tags", []):
            groups[tag].append(bool(row["passed"]))
    return {tag: (sum(values), len(values)) for tag, values in sorted(groups.items())}


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m evals.report <before.jsonl> <after.jsonl>")
    before, after = load(sys.argv[1]), load(sys.argv[2])
    before_by = {row["case"]["id"]: row for row in before}
    after_by = {row["case"]["id"]: row for row in after}
    bp, bn = rate(before)
    ap, an = rate(after)
    fixed, broke = [], []
    for case_id in sorted(set(before_by) | set(after_by)):
        b = before_by.get(case_id, {}).get("passed")
        a = after_by.get(case_id, {}).get("passed")
        if b is False and a is True:
            fixed.append(case_id)
        elif b is True and a is False:
            broke.append(case_id)

    def esc(value) -> str:
        return html.escape(str(value if value is not None else ""))

    rows_html = []
    for case_id in sorted(set(before_by) | set(after_by)):
        b = before_by.get(case_id, {}).get("passed")
        a = after_by.get(case_id, {}).get("passed")
        change = "fixed" if case_id in fixed else "regressed" if case_id in broke else ""
        rows_html.append(
            f"<tr class='{change}'><td>{esc(case_id)}</td><td>{esc(b)}</td><td>{esc(a)}</td><td>{esc(change)}</td></tr>"
        )
    examples = []
    for case_id in ("privacy-address", "standard-late-pp1005", "off-topic-injection", "late-refund"):
        row = after_by.get(case_id) or before_by.get(case_id)
        if not row:
            continue
        judge = row.get("judge") or {}
        examples.append(
            f"<h3>{esc(case_id)}</h3>"
            f"<p>Passed: {esc(row['passed'])}. Judge: {esc(judge.get('score'))}/5. {esc(judge.get('reason'))}</p>"
            f"<pre>{esc(row['result'].get('answer', ''))}</pre>"
        )
    tag_line = ", ".join(f"{tag} {passed}/{total}" for tag, (passed, total) in by_tag(after).items())
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Parcel Pigeon evaluation</title>
<style>
body {{ font-family: Georgia, serif; margin: 2rem auto; max-width: 52rem; line-height: 1.45; color: #1c1917; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border-bottom: 1px solid #d6d3d1; text-align: left; padding: 0.35rem; font-size: 0.95rem; }}
tr.fixed {{ background: #ecfdf3; }}
tr.regressed {{ background: #fef2f2; }}
pre {{ white-space: pre-wrap; background: #f5f5f4; padding: 0.8rem; }}
</style>
</head>
<body>
<h1>Parcel Pigeon scorecard</h1>
<p>Before {esc(bp)}/{esc(bn)}. After {esc(ap)}/{esc(an)}. Fixed: {esc(', '.join(fixed) or 'none')}. Regressed: {esc(', '.join(broke) or 'none')}.</p>
<p>After, by tag: {esc(tag_line)}</p>
<p>Sources: {esc(sys.argv[1])} and {esc(sys.argv[2])}. These figures are only for the runs named above.</p>
<table>
<thead><tr><th>Case</th><th>Before</th><th>After</th><th>Change</th></tr></thead>
<tbody>
{''.join(rows_html)}
</tbody>
</table>
<h2>Examples from the after file, or the before file if that case is absent</h2>
{''.join(examples)}
</body>
</html>
"""
    out = Path("demo") / "report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
