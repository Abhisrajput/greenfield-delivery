"""Tests for the conformance checker.

Every fixture is evaluated in a temporary copy OUTSIDE this repository. That
is not incidental tidiness: `examples/conformance/*` live inside the greenfield
repo, so running the checker on them in place resolves git questions against
greenfield's own history, and a fixture meant to demonstrate one rule picks up
unrelated failures from a placeholder SHA. Copying out gives each fixture the
git context it is supposed to have — usually none.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import conform  # noqa: E402
from dashboard import history, parse  # noqa: E402
from dashboard.serve import ENGAGEMENT_DIR, _resolve_artifact_status  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "examples" / "conformance"


def _evaluate(root: Path) -> dict:
    """Run every rule against `root`, returning {rule: status}."""
    def read(name):
        try:
            return (root / ENGAGEMENT_DIR / name).read_text(encoding="utf-8")
        except OSError:
            return None

    engagement = parse.parse_engagement(read("engagement.md"))
    reqs = parse.parse_requirements(read("requirements.md"))
    tasks = parse.parse_tasks(read("tasks.md"))
    signoffs = parse.parse_signoffs(read("signoffs.md"))
    cases = parse.parse_test_cases(read("test-cases.md"))
    decisions = parse.parse_decisions(read("decisions.md"))
    history_ok = history.is_repo(root)
    status, present = {}, {}
    if history_ok and signoffs.present:
        for s in signoffs.signoffs:
            present[s.commit] = history.commit_exists(root, s.commit)
            status[(s.commit, s.artifact)] = _resolve_artifact_status(root, s.commit, s.artifact)
    results = conform.check_all(engagement, reqs, tasks, signoffs, status, history_ok,
                                present, cases, decisions)
    return {r.rule: r.status for r in results}


class FixtureCase(unittest.TestCase):
    def evaluate(self, name: str, git: bool = False) -> dict:
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = Path(tmp) / name
        shutil.copytree(FIXTURES / name, root)
        if git:
            for args in (("init", "-q", "-b", "main"),
                         ("config", "user.email", "t@example.com"),
                         ("config", "user.name", "T"),
                         ("add", "-A"),
                         ("commit", "-q", "-m", "fixture")):
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
        return _evaluate(root)


class TestFixturesFailTheRuleTheyDemonstrate(FixtureCase):
    def test_gate_out_of_order(self):
        # Design is signed; Requirements never was. Without git this fixture
        # demonstrates G1 alone.
        self.assertEqual(self.evaluate("gate-out-of-order")["G1"], conform.FAIL)

    def test_missing_commit(self):
        # Needs a real repository, or there is nothing for the recorded SHA to
        # be absent FROM: without git, G2 is honestly "not checked".
        self.assertEqual(self.evaluate("missing-commit", git=True)["G2"], conform.FAIL)
        self.assertEqual(self.evaluate("missing-commit")["G2"], conform.SKIP)

    def test_duplicate_requirement_id(self):
        self.assertEqual(self.evaluate("duplicate-req-id")["R2"], conform.FAIL)

    def test_requirement_without_a_criterion(self):
        self.assertEqual(self.evaluate("no-criterion")["R3"], conform.FAIL)

    def test_task_pointing_at_a_requirement_that_does_not_exist(self):
        self.assertEqual(self.evaluate("dangling-task")["T3"], conform.FAIL)

    def test_requirement_with_no_test_case(self):
        # R2 exists and is in scope; nothing tests it. It can be assumed met,
        # never accepted against evidence.
        self.assertEqual(self.evaluate("untested-requirement")["C2"], conform.FAIL)

    def test_out_of_scope_items_do_not_need_test_cases(self):
        # An earlier version of this test asserted on C1, which has nothing to
        # do with out-of-scope items — it could not fail for the reason its
        # name gives, and a mutation removing the out-of-scope exclusion sailed
        # past it. Constructed directly so that every IN-scope requirement is
        # covered and only the out-of-scope one is not: C2 must still pass.
        reqs = parse.parse_requirements(
            "## Functional\n\n"
            "| ID | Requirement | Acceptance criteria |\n|---|---|---|\n"
            "| R1 | Do the thing | It is done |\n\n"
            "## Out of scope\n\n"
            "| ID | Item | Note |\n|---|---|---|\n"
            "| X1 | Not this | Next quarter |\n"
        )
        cases = parse.parse_test_cases(
            "| ID | Req | Mode | Scenario | Given | When | Then | Result |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| TC1 | R1 | manual | Do it | Ready | User does it | It is visible | pass |\n"
        )
        results = {r.rule: r for r in conform.check_all(
            parse.parse_engagement(None), reqs, parse.parse_tasks(None),
            parse.parse_signoffs(None), {}, False, {}, cases)}
        self.assertEqual(results["C2"].status, conform.PASS, results["C2"].detail)
        self.assertNotIn("X1", results["C2"].detail)


class TestFixturesDoNotFailAnythingElse(FixtureCase):
    """The half that makes the suite meaningful. A checker that fails
    everything discriminates no better than one that fails nothing."""

    EXPECTED = {
        "gate-out-of-order": {"G1"},
        "duplicate-req-id": {"R2"},
        "no-criterion": {"R3"},
        "dangling-task": {"T3"},
        "untested-requirement": {"C2"},
    }

    def test_each_fixture_breaks_exactly_one_rule(self):
        for name, expected in self.EXPECTED.items():
            with self.subTest(fixture=name):
                results = self.evaluate(name)
                failed = {rule for rule, status in results.items() if status == conform.FAIL}
                self.assertEqual(failed, expected)


class TestNotStartedIsNotCompliant(FixtureCase):
    def test_an_empty_engagement_reports_skips_not_passes(self):
        # The most important case. A new engagement has no requirements, no
        # tasks and no sign-offs. Grading that as compliant would make the
        # checker actively misleading — it would certify every engagement on
        # its first day.
        results = self.evaluate("not-started")
        self.assertNotIn(conform.FAIL, results.values())
        for rule in ("G1", "G2", "G3", "R1", "R2", "R3", "T1", "T2", "T3",
                     "C1", "C2", "D1", "D2"):
            self.assertEqual(results[rule], conform.SKIP, rule)
        # engagement.md is the one thing that does exist, so it is checked.
        self.assertEqual(results["E1"], conform.PASS)

    def test_skips_are_reported_and_never_counted_as_passes(self):
        results = conform.check_all(
            parse.parse_engagement(None), parse.parse_requirements(None),
            parse.parse_tasks(None), parse.parse_signoffs(None), {}, False, {},
            parse.parse_test_cases(None), parse.parse_decisions(None),
        )
        text = conform.report(results)
        self.assertIn("not checked", text)
        self.assertIn("A check that could not run is not a check that passed.", text)


class TestAutomatedCasesRule(unittest.TestCase):
    """C3 has three states, and getting this wrong makes it useless.

    Failing from the moment automated cases are written — which is the Design
    gate, before any step definitions exist — would leave the check red for the
    entire build phase. A check that is always red is one a team learns to
    ignore, and then it is not a check.
    """

    HEADER = ("| ID | Req | Mode | Scenario | Given | When | Then | Result |\n"
              "|---|---|---|---|---|---|---|---|\n")

    def _c3(self, *rows):
        cases = parse.parse_test_cases(self.HEADER + "".join(rows))
        results = {r.rule: r for r in conform.check_all(
            parse.parse_engagement(None), parse.parse_requirements(None),
            parse.parse_tasks(None), parse.parse_signoffs(None), {}, False, {}, cases)}
        return results["C3"]

    def test_nothing_automated_is_not_a_failure(self):
        got = self._c3("| TC1 | R1 | manual | S | G | W | T | not run |\n")
        self.assertEqual(got.status, conform.SKIP)

    def test_suite_not_wired_up_yet_is_not_a_failure(self):
        # Every automated case still at `not run`: nobody has written step
        # definitions. Ordinary from the Design gate onward.
        got = self._c3(
            "| TC1 | R1 | automated | A | G | W | T | not run |\n",
            "| TC2 | R1 | automated | B | G | W | T | not run |\n",
        )
        self.assertEqual(got.status, conform.SKIP)
        self.assertIn("step definitions", got.detail)

    def test_a_case_skipped_inside_a_live_suite_fails(self):
        # THIS is the defect the rule exists for: the suite runs, reports green,
        # and TC2 is quietly never executed.
        got = self._c3(
            "| TC1 | R1 | automated | A | G | W | T | pass |\n",
            "| TC2 | R1 | automated | B | G | W | T | not run |\n",
        )
        self.assertEqual(got.status, conform.FAIL)
        self.assertIn("TC2", got.detail)

    def test_a_failing_case_is_not_a_stalled_case(self):
        # `fail` is a result. The suite ran it and it did not pass — a
        # conversation, not a gap in the suite.
        got = self._c3(
            "| TC1 | R1 | automated | A | G | W | T | pass |\n",
            "| TC2 | R1 | automated | B | G | W | T | fail |\n",
        )
        self.assertEqual(got.status, conform.PASS)


class TestScaffoldedEngagement(FixtureCase):
    """What /new-engagement writes on day one."""

    def test_the_scaffold_parses_cleanly(self):
        # The command tells the reader to create these files. If the scaffold
        # it describes does not parse, the very first thing anyone does with
        # this plugin produces a broken engagement.
        results = self.evaluate("scaffolded")
        for rule in ("E1", "R1", "T1"):
            self.assertEqual(results[rule], conform.PASS, rule)

    def test_empty_tables_are_not_passing_tables(self):
        # The defect this pins: every rule over an empty collection was
        # trivially true, so a scaffolded engagement reported 10 passed and
        # 0 failed. "Requirement IDs are unique" over zero requirements is
        # true and useless, and reporting it as a pass certifies an engagement
        # before it has begun.
        results = self.evaluate("scaffolded")
        self.assertNotIn(conform.FAIL, results.values())
        for rule in ("G1", "G2", "G3", "R2", "R3", "T2", "T3"):
            self.assertEqual(results[rule], conform.SKIP, rule)
        passed = [r for r, st in results.items() if st == conform.PASS]
        self.assertEqual(sorted(passed), ["E1", "R1", "T1"])


class TestSampleEngagement(FixtureCase):
    def test_the_sample_fails_g3_because_scope_drifted(self):
        # examples/make-sample.sh deliberately changes an acceptance criterion
        # after the Requirements gate is signed. If this ever passes, either
        # the sample stopped demonstrating drift or G3 stopped detecting it.
        script = FIXTURES.parent / "make-sample.sh"
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = Path(tmp) / "sample"
        subprocess.run([str(script), str(root)], check=True, capture_output=True)
        results = _evaluate(root)
        self.assertEqual(results["G3"], conform.FAIL)
        self.assertEqual(results["G1"], conform.PASS)
        self.assertEqual(results["G2"], conform.PASS)
        # The sample also ships a requirement (N1) that nothing plans and
        # nothing tests, so C2 fails while the file itself is well-formed.
        self.assertEqual(results["C1"], conform.PASS)
        self.assertEqual(results["C2"], conform.FAIL)


class TestExitCode(unittest.TestCase):
    def test_failures_exit_nonzero_and_a_clean_run_exits_zero(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        clean = Path(tmp) / "clean"
        shutil.copytree(FIXTURES / "not-started", clean)
        self.assertEqual(conform.main(["--root", str(clean)]), 0)
        broken = Path(tmp) / "broken"
        shutil.copytree(FIXTURES / "duplicate-req-id", broken)
        self.assertEqual(conform.main(["--root", str(broken)]), 1)


if __name__ == "__main__":
    unittest.main()
