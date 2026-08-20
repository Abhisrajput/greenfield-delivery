"""Generate Gherkin from `test-cases.md`, and read run results back into it.

**The direction is the whole design.** Feature files are generated FROM
`test-cases.md`, never the other way round. Author Gherkin first and developers
own the specification, the business stops reading it, and you have paid the
entire cost of a translation layer for none of its benefit — which is how BDD
usually dies. `test-cases.md` stays the source of truth and stays readable by
the client.

Generated files are therefore disposable. They carry a "do not edit" banner and
are safe to delete and regenerate; anything worth keeping belongs in
`test-cases.md`.

**This adds no dependencies, and deliberately runs nothing.** There is no test
runner here and there will not be one: a runner means Cucumber or Behave or
pytest-bdd plus a browser driver, per stack, which is exactly the dependency
tree this plugin exists without. The runner and the step definitions live in the
CLIENT's repository, in the client's own stack. This script hands that repo a
`.feature` file and reads back a standard Cucumber JSON report.

Two commands:

    python3 scripts/features.py generate --root <engagement> --out features/
    python3 scripts/features.py results  --root <engagement> --report cucumber.json

`generate` writes one feature file per requirement. `results` maps scenarios
back to case IDs by tag and rewrites the `Result` column.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from dashboard import parse  # noqa: E402
from dashboard.serve import ENGAGEMENT_DIR  # noqa: E402

BANNER = (
    "# Generated from docs/engagement/test-cases.md — do not edit.\n"
    "# Edit the test case and regenerate: python3 scripts/features.py generate\n"
)

# Cucumber's JSON report is the one format Cucumber, Behave, pytest-bdd (via
# its report plugins) and SpecFlow all agree on, so reading it keeps this
# script independent of which runner the client's stack uses.
_CUCUMBER_TO_RESULT = {
    "passed": "pass",
    "failed": "fail",
    "skipped": "blocked",
    "pending": "not run",
    "undefined": "not run",
}


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def feature_for(req_id: str, req_text: str, cases) -> str:
    """One feature per requirement, so a reader sees every way a requirement
    can be proved in one place — and sees at a glance when there is only one."""
    lines = [BANNER, f"Feature: {req_id} — {req_text}", ""]
    for case in cases:
        # The case ID is a tag so results can be mapped back unambiguously.
        # Matching on scenario text instead would break the moment someone
        # improves the wording, which they should be free to do.
        lines.append(f"  @{case.id} @{case.req} @{case.mode}")
        lines.append(f"  Scenario: {case.scenario}")
        if case.given:
            lines.append(f"    Given {case.given}")
        if case.when:
            lines.append(f"    When {case.when}")
        lines.append(f"    Then {case.then}")
        lines.append("")
    return "\n".join(lines)


def generate(cases_file, reqs_file) -> dict:
    """{filename: contents}. Pure."""
    req_text = {r.id: r.text for r in reqs_file.requirements} if reqs_file.present else {}
    by_req: dict = {}
    for case in cases_file.cases:
        by_req.setdefault(case.req, []).append(case)

    out = {}
    for req_id, group in by_req.items():
        # A requirement absent from requirements.md is named as unknown rather
        # than given an invented title — the same rule as everywhere else here.
        text = req_text.get(req_id, "(not in requirements.md)")
        out[f"{_slug(req_id)}.feature"] = feature_for(req_id, text, group)
    return out


def results_from_report(report: dict | list) -> dict:
    """{case_id: result} from a Cucumber JSON report. Pure.

    A scenario with no steps is reported as `not run` rather than as passing:
    an empty scenario trivially has no failing step, and reading that as a pass
    is how a suite reports green having verified nothing.
    """
    features = report if isinstance(report, list) else report.get("features", [])
    found = {}
    for feature in features:
        for element in feature.get("elements", []):
            tags = [t.get("name", "").lstrip("@") for t in element.get("tags", [])]
            case_ids = [t for t in tags if t.startswith("TC")]
            if not case_ids:
                continue
            steps = element.get("steps", [])
            if not steps:
                found[case_ids[0]] = "not run"
                continue
            statuses = [s.get("result", {}).get("status", "undefined") for s in steps]
            if "failed" in statuses:
                verdict = "fail"
            elif all(s == "passed" for s in statuses):
                verdict = "pass"
            else:
                # Anything else — skipped, pending, undefined — is NOT a pass.
                first = next((s for s in statuses if s != "passed"), "undefined")
                verdict = _CUCUMBER_TO_RESULT.get(first, "not run")
            found[case_ids[0]] = verdict
    return found


def apply_results(text: str, results: dict) -> tuple[str, int]:
    """Rewrite the Result cell for each case named in `results`. Pure.

    Only rows whose ID appears in the report are touched. A case the runner did
    not report keeps whatever it had — usually `not run` — because absence from
    a report is not evidence of anything.
    """
    lines = text.splitlines()
    changed = 0
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(parse.TESTS_HEADER) or cells[0] not in results:
            continue
        if cells[-1] == results[cells[0]]:
            continue
        cells[-1] = results[cells[0]]
        lines[index] = "| " + " | ".join(cells) + " |"
        changed += 1
    return "\n".join(lines) + "\n", changed


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("generate", "results"):
        print(__doc__)
        return 2
    command = args[0]

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    root = Path(opt("--root", ".")).resolve()
    cases_path = root / ENGAGEMENT_DIR / "test-cases.md"
    try:
        cases_text = cases_path.read_text(encoding="utf-8")
    except OSError:
        print(f"No {cases_path}. Produce test cases first — see the "
              "business-test-cases skill.", file=sys.stderr)
        return 1

    cases = parse.parse_test_cases(cases_text)
    if not cases.header_ok:
        print(f"{cases_path} does not have the canonical header; refusing to "
              "guess at its columns.", file=sys.stderr)
        return 1
    if cases.problems:
        # Generating from a partly-readable file would silently drop the rows
        # that failed to parse, and the feature suite would look complete.
        for problem in cases.problems:
            print(f"  {problem.message}", file=sys.stderr)
        print("Fix test-cases.md first — generating now would drop the rows "
              "above without saying so.", file=sys.stderr)
        return 1

    if command == "generate":
        out_dir = Path(opt("--out", root / "features"))
        reqs_path = root / ENGAGEMENT_DIR / "requirements.md"
        try:
            reqs = parse.parse_requirements(reqs_path.read_text(encoding="utf-8"))
        except OSError:
            reqs = parse.parse_requirements(None)
        files = generate(cases, reqs)
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, content in sorted(files.items()):
            (out_dir / name).write_text(content, encoding="utf-8")
        automated = sum(1 for c in cases.cases if c.mode == "automated")
        print(f"Wrote {len(files)} feature file(s) to {out_dir}")
        print(f"  {len(cases.cases)} scenarios, {automated} tagged @automated")
        if automated < len(cases.cases):
            manual = len(cases.cases) - automated
            print(f"  {manual} {'is' if manual == 1 else 'are'} @manual — a person "
                  "runs those and records the result by hand.")
        return 0

    report_path = opt("--report")
    if not report_path:
        print("results needs --report <cucumber.json>", file=sys.stderr)
        return 1
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Could not read {report_path}: {exc}", file=sys.stderr)
        return 1

    found = results_from_report(report)
    if not found:
        print("No scenarios in that report carried a @TC tag — nothing to map "
              "back. Regenerate the feature files.", file=sys.stderr)
        return 1
    updated, changed = apply_results(cases_text, found)
    cases_path.write_text(updated, encoding="utf-8")
    unreported = [c.id for c in cases.cases
                  if c.mode == "automated" and c.id not in found]
    print(f"Updated {changed} result(s) in {cases_path} from {len(found)} reported "
          "scenario(s)")
    if unreported:
        # Named rather than counted: an automated case the runner never
        # mentioned is usually a scenario nobody implemented steps for, and it
        # is invisible in a summary that only reports passes.
        print("  automated but absent from the report: " + ", ".join(unreported))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
