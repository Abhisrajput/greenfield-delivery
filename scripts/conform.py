"""Conformance checks for an engagement.

**What this evaluates, and what it does not.**

It reads the artifacts an engagement produced and asks whether they obey the
rules the methodology states: gates signed in order, approvals that still cover
the file they approved, identifiers that are unique, tasks that point at
requirements which exist. Those are the observable evidence that the method was
followed.

It does NOT evaluate the *quality* of anyone's judgment, and it cannot tell you
whether a requirement is the right requirement. An engagement can pass every
check here and still be badly run. Treat a pass as "the record is
well-formed and internally consistent", never as "this was done well".

Three outcomes, and the third matters as much as the other two:

  pass  — the rule was checked and holds.
  fail  — the rule was checked and is broken.
  skip  — the rule COULD NOT be checked (no git, file absent, gate not
          reached yet). A skip is never a pass. `python3 scripts/conform.py`
          prints skips and says how many; it exits non-zero only on failures,
          because "not yet reached" is the normal state of a live engagement.

`check_all` is pure: it takes parsed files and a status mapping and returns
results. Every file read, git call and clock read lives in `main`, matching the
split the dashboard package already uses.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from dashboard import analyse, history, parse  # noqa: E402
from dashboard.serve import ENGAGEMENT_DIR, _resolve_artifact_status  # noqa: E402

PASS, FAIL, SKIP = "pass", "fail", "skip"


@dataclass(frozen=True)
class Result:
    rule: str
    name: str
    status: str
    detail: str


# Which gate cannot be signed before which, taken from commands/gate.md. Only
# these three are blocked: Discovery is first, and Requirements is deliberately
# NOT blocked by Discovery — Discovery gates the commercial shape, not the
# scope baseline, and may be skipped entirely.
BLOCKED_BY = {
    "design": "requirements",
    "build": "design",
    "handoff": "design",
}


def _duplicates(ids) -> list:
    seen, dupes = set(), []
    for identifier in ids:
        if identifier in seen and identifier not in dupes:
            dupes.append(identifier)
        seen.add(identifier)
    return dupes


def check_all(engagement, reqs, tasks, signoffs, signoff_status, history_ok: bool,
              commit_present=None, cases=None, decisions=None):
    """Every rule, in a fixed order. Pure."""
    out: list[Result] = []
    commit_present = commit_present or {}
    signed = {s.gate.lower(): s for s in signoffs.signoffs} if signoffs.present else {}

    # ---- E: the engagement file ------------------------------------------
    if not engagement.present:
        out.append(Result("E1", "engagement.md exists", FAIL,
                          f"no {ENGAGEMENT_DIR}/engagement.md — this is not an engagement"))
    elif engagement.problems:
        out.append(Result("E1", "engagement.md is well-formed", FAIL,
                          "; ".join(p.message for p in engagement.problems)))
    else:
        out.append(Result("E1", "engagement.md is well-formed", PASS, "all blocks present"))

    # ---- G1: gates signed in order ---------------------------------------
    # `present` is not the same as `has rows`. /new-engagement scaffolds
    # signoffs.md with an empty table, and every gate rule over zero sign-offs
    # is trivially true — which reported a day-one engagement as three passes.
    if not signoffs.present or not signoffs.signoffs:
        why = ("no signoffs.md yet" if not signoffs.present
               else "no gate has been signed off yet")
        out.append(Result("G1", "gates signed in order", SKIP, why))
    else:
        broken = [
            f"{gate} is signed but {needs} is not"
            for gate, needs in BLOCKED_BY.items()
            if gate in signed and needs not in signed
        ]
        out.append(Result("G1", "gates signed in order",
                          FAIL if broken else PASS,
                          "; ".join(broken) if broken else "no gate precedes its prerequisite"))

    # ---- G2/G3: approvals still cover what they approved ------------------
    if not signoffs.present or not signoffs.signoffs:
        why = ("no signoffs.md yet" if not signoffs.present
               else "no gate has been signed off yet")
        out.append(Result("G2", "sign-off commits exist", SKIP, why))
        out.append(Result("G3", "approved artifacts unchanged", SKIP, why))
    elif not history_ok:
        # The honest-failure rule: git could not be read, so these are unknown.
        # Reporting them as passes would manufacture assurance; reporting them
        # as failures would blame the engagement for the environment.
        out.append(Result("G2", "sign-off commits exist", SKIP, "not a git repository"))
        out.append(Result("G3", "approved artifacts unchanged", SKIP, "not a git repository"))
    else:
        # Only the approval that currently counts for each gate — see
        # analyse.current_signoffs. A superseded row is history, not a live
        # failure, and conform disagreeing with the dashboard about the same
        # gate is worse than either answer alone.
        live = analyse.current_signoffs(signoffs)
        missing, unknown_commit = [], []
        for signoff in live:
            # `commit_present` is a separate question from `signoff_status`,
            # which answers "unverifiable" for a missing commit AND for a path
            # that was not in the tree yet. Asking only the latter meant a
            # sign-off pointing at a commit that does not exist reported PASS
            # here — the report asserting an approval it had never checked.
            present = commit_present.get(signoff.commit)
            if present is False:
                missing.append(f"{signoff.gate}: commit {signoff.commit} not in this repository")
            elif present is None:
                unknown_commit.append(f"{signoff.gate}: could not check {signoff.commit}")
        if missing:
            out.append(Result("G2", "sign-off commits exist", FAIL, "; ".join(missing)))
        elif unknown_commit:
            out.append(Result("G2", "sign-off commits exist", SKIP, "; ".join(unknown_commit)))
        else:
            out.append(Result("G2", "sign-off commits exist", PASS,
                              "every recorded commit is present"))

        changed, unknown = [], []
        for signoff in live:
            if commit_present.get(signoff.commit) is not True:
                continue  # already reported by G2; do not blame the artifact
            status = signoff_status.get((signoff.commit, signoff.artifact))
            if status == "changed":
                changed.append(f"{signoff.artifact} changed since {signoff.commit}")
            elif status != "unchanged":
                unknown.append(f"{signoff.gate}: cannot compare {signoff.artifact}")
        if changed:
            out.append(Result("G3", "approved artifacts unchanged", FAIL, "; ".join(changed)))
        elif unknown:
            out.append(Result("G3", "approved artifacts unchanged", SKIP, "; ".join(unknown)))
        else:
            out.append(Result("G3", "approved artifacts unchanged", PASS,
                              "no approved artifact has changed since sign-off"))

    # ---- R: requirements --------------------------------------------------
    if not reqs.present:
        out.append(Result("R1", "requirements.md exists", SKIP,
                          "not written yet — the Requirements gate has not run"))
        out.append(Result("R2", "requirement IDs are unique", SKIP, "no requirements.md"))
        out.append(Result("R3", "every requirement has a criterion", SKIP, "no requirements.md"))
    else:
        out.append(Result("R1", "requirements.md is well-formed",
                          FAIL if reqs.problems else PASS,
                          "; ".join(p.message for p in reqs.problems) or "parses cleanly"))
        # A rule over an empty collection is not a rule that passed. The
        # /new-engagement scaffold writes requirements.md with empty tables, so
        # on day one "IDs are unique" and "every requirement has a criterion"
        # were both trivially true and the report read 10 passed, 0 failed —
        # an engagement certified compliant before anyone had written a word.
        # Same principle as `skip`, arriving through a different door.
        if not reqs.requirements:
            out.append(Result("R2", "requirement IDs are unique", SKIP,
                              "no requirements written yet"))
            out.append(Result("R3", "every requirement has a criterion", SKIP,
                              "no requirements written yet"))
        else:
            dupes = _duplicates([r.id for r in reqs.requirements])
            out.append(Result("R2", "requirement IDs are unique",
                              FAIL if dupes else PASS,
                              ("duplicate: " + ", ".join(dupes)) if dupes
                              else f"{len(reqs.requirements)} unique identifiers"))
            # Out-of-scope rows carry a note rather than a criterion; only
            # in-scope requirements are held to this.
            empty = [r.id for r in reqs.requirements
                     if r.kind != "out-of-scope" and not r.criterion.strip()]
            out.append(Result("R3", "every requirement has a criterion",
                              FAIL if empty else PASS,
                              ("no acceptance criterion: " + ", ".join(empty)) if empty
                              else "every in-scope requirement states how it is checked"))

    # ---- T: tasks ---------------------------------------------------------
    if not tasks.present:
        out.append(Result("T1", "tasks.md is well-formed", SKIP,
                          "not written yet — produced at the Design gate"))
        out.append(Result("T2", "task IDs are unique", SKIP, "no tasks.md"))
        out.append(Result("T3", "every task points at a real requirement", SKIP, "no tasks.md"))
    else:
        problems = [p.message for p in tasks.problems]
        if not tasks.header_ok:
            problems.insert(0, "header row is not the canonical one")
        out.append(Result("T1", "tasks.md is well-formed",
                          FAIL if problems else PASS,
                          "; ".join(problems) or "canonical header, every row readable"))
        if not tasks.tasks:
            out.append(Result("T2", "task IDs are unique", SKIP,
                              "no tasks written yet — produced at the Design gate"))
        else:
            dupes = _duplicates([t.id for t in tasks.tasks])
            out.append(Result("T2", "task IDs are unique",
                              FAIL if dupes else PASS,
                              ("duplicate: " + ", ".join(dupes)) if dupes
                              else f"{len(tasks.tasks)} unique identifiers"))
        if not tasks.tasks:
            out.append(Result("T3", "every task points at a real requirement", SKIP,
                              "no tasks written yet"))
        elif not reqs.present:
            out.append(Result("T3", "every task points at a real requirement", SKIP,
                              "no requirements.md to check against"))
        else:
            bad = [t.id for t in analyse.dangling(reqs, tasks)]
            out.append(Result("T3", "every task points at a real requirement",
                              FAIL if bad else PASS,
                              ("points at a requirement that does not exist: " + ", ".join(bad))
                              if bad else "every Req cell resolves, or is 'none'"))
    # ---- C: test cases ----------------------------------------------------
    if cases is None or not cases.present:
        out.append(Result("C1", "test-cases.md is well-formed", SKIP,
                          "not written yet — produced at the Design gate"))
        out.append(Result("C2", "every in-scope requirement has a test case", SKIP,
                          "no test-cases.md"))
        out.append(Result("C3", "automated cases have actually run", SKIP,
                          "no test-cases.md"))
    else:
        problems = [p.message for p in cases.problems]
        if not cases.header_ok:
            problems.insert(0, "header row is not the canonical one")
        out.append(Result("C1", "test-cases.md is well-formed",
                          FAIL if problems else PASS,
                          "; ".join(problems) or "canonical header, every row readable"))
        if not reqs.present:
            out.append(Result("C2", "every in-scope requirement has a test case", SKIP,
                              "no requirements.md to check against"))
        else:
            covered = {c.req for c in cases.cases}
            # Out-of-scope items are the list of things deliberately NOT built;
            # a test case against one would be a contradiction, not coverage.
            in_scope = [r for r in reqs.requirements if r.kind != "out-of-scope"]
            if not in_scope:
                out.append(Result("C2", "every in-scope requirement has a test case",
                                  SKIP, "no in-scope requirements written yet"))
                in_scope = None
            uncovered = ([] if in_scope is None else
                         [r.id for r in in_scope if r.id not in covered])
            if in_scope is not None:
                out.append(Result("C2", "every in-scope requirement has a test case",
                                  FAIL if uncovered else PASS,
                                  ("no test case: " + ", ".join(uncovered)) if uncovered
                                  else "every in-scope requirement can be accepted "
                                       "against a case"))

        # An automated case sitting at `not run` is the quiet failure of this
        # pipeline: a feature file was generated, nobody implemented steps for
        # it, and the suite reports green on everything it DID run. Manual cases
        # are held to a different standard on purpose — a person has to get to
        # them, and "not yet" is an ordinary state mid-engagement, not a defect.
        automated = [c for c in cases.cases if c.mode == "automated"]
        stalled = [c.id for c in automated if c.result == "not run"]
        if not automated:
            out.append(Result("C3", "automated cases have actually run", SKIP,
                              "no cases are marked automated"))
        elif len(stalled) == len(automated):
            # NONE have run: the suite has not been wired up yet. That is the
            # ordinary state from the Design gate until someone writes step
            # definitions, and failing throughout would make this red for the
            # whole build phase — which is how a team learns to ignore it.
            out.append(Result("C3", "automated cases have actually run", SKIP,
                              f"no automated case has run yet ({len(automated)} waiting "
                              "on step definitions)"))
        else:
            # SOME have run and some have not. The suite is live, and these are
            # being skipped inside a run that reports green on everything else —
            # which is the failure this rule exists to catch.
            out.append(Result("C3", "automated cases have actually run",
                              FAIL if stalled else PASS,
                              ("the suite runs, but these never do: " + ", ".join(stalled))
                              if stalled else
                              f"all {len(automated)} automated cases have a recorded result"))

    # ---- D: decisions ------------------------------------------------------
    # Optional by design. A solo engagement keeps its decisions in one head
    # accurately enough; absent is not a failing, so this skips rather than
    # fails when the file is not there.
    if decisions is None or not decisions.present:
        out.append(Result("D1", "decisions.md is well-formed", SKIP,
                          "no decisions.md — optional, and worth having on a team"))
        out.append(Result("D2", "decision IDs are unique", SKIP, "no decisions.md"))
    else:
        problems = [p.message for p in decisions.problems]
        if not decisions.header_ok:
            problems.insert(0, "header row is not the canonical one")
        out.append(Result("D1", "decisions.md is well-formed",
                          FAIL if problems else PASS,
                          "; ".join(problems) or "canonical header, every row carries its reason"))
        if not decisions.decisions:
            out.append(Result("D2", "decision IDs are unique", SKIP,
                              "no decisions recorded yet"))
        else:
            dupes = _duplicates([d.id for d in decisions.decisions])
            out.append(Result("D2", "decision IDs are unique",
                              FAIL if dupes else PASS,
                              ("duplicate: " + ", ".join(dupes)) if dupes
                              else f"{len(decisions.decisions)} recorded"))

    return tuple(out)


_GLYPH = {PASS: "PASS", FAIL: "FAIL", SKIP: "skip"}


def report(results) -> str:
    lines = []
    for r in results:
        lines.append(f"  {_GLYPH[r.status]:4}  {r.rule:3} {r.name}")
        if r.status != PASS:
            lines.append(f"          {r.detail}")
    failed = sum(1 for r in results if r.status == FAIL)
    skipped = sum(1 for r in results if r.status == SKIP)
    passed = sum(1 for r in results if r.status == PASS)
    lines.append("")
    summary = f"{passed} passed, {failed} failed, {skipped} not checked"
    lines.append(summary)
    if skipped:
        # Said explicitly, because a skip silently counted as a pass is the
        # failure mode this whole file exists to avoid.
        lines.append("A check that could not run is not a check that passed.")
    return "\n".join(lines)


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[args.index("--root") + 1] if "--root" in args else ".").resolve()

    def read(name):
        path = root / ENGAGEMENT_DIR / name
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    engagement = parse.parse_engagement(read("engagement.md"))
    reqs = parse.parse_requirements(read("requirements.md"))
    tasks = parse.parse_tasks(read("tasks.md"))
    signoffs = parse.parse_signoffs(read("signoffs.md"))
    cases = parse.parse_test_cases(read("test-cases.md"))
    decisions = parse.parse_decisions(read("decisions.md"))

    history_ok = history.is_repo(root)
    signoff_status, commit_present = {}, {}
    if history_ok and signoffs.present:
        for s in signoffs.signoffs:
            commit_present[s.commit] = history.commit_exists(root, s.commit)
            signoff_status[(s.commit, s.artifact)] = _resolve_artifact_status(
                root, s.commit, s.artifact
            )

    results = check_all(engagement, reqs, tasks, signoffs, signoff_status, history_ok,
                        commit_present, cases, decisions)
    print(f"Conformance — {root}")
    print(report(results))
    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
