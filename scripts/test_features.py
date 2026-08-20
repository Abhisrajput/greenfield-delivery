"""Tests for the Gherkin generator and the result import.

The properties worth pinning here are all about a suite being unable to claim
more than it verified.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import features  # noqa: E402
from dashboard import parse  # noqa: E402

HEADER = (
    "| ID | Req | Mode | Scenario | Given | When | Then | Result |\n"
    "|---|---|---|---|---|---|---|---|\n"
)
REQS = (
    "## Functional\n\n"
    "| ID | Requirement | Acceptance criteria |\n|---|---|---|\n"
    "| R1 | Submit orders | It works |\n"
)


def _cases(*rows):
    return parse.parse_test_cases(HEADER + "".join(rows))


class TestGeneration(unittest.TestCase):
    def test_scenario_carries_its_case_id_as_a_tag(self):
        # Results map back by tag, never by scenario text — text must stay free
        # to improve without silently breaking the mapping.
        out = features.generate(
            _cases("| TC1 | R1 | automated | Submit | Ready | They submit | It appears | not run |\n"),
            parse.parse_requirements(REQS),
        )
        feature = out["r1.feature"]
        self.assertIn("@TC1 @R1 @automated", feature)
        self.assertIn("Scenario: Submit", feature)
        self.assertIn("Given Ready", feature)
        self.assertIn("When They submit", feature)
        self.assertIn("Then It appears", feature)

    def test_generated_files_say_they_are_generated(self):
        out = features.generate(
            _cases("| TC1 | R1 | manual | S | G | W | T | not run |\n"),
            parse.parse_requirements(REQS),
        )
        self.assertIn("do not edit", out["r1.feature"])

    def test_a_requirement_absent_from_requirements_md_is_named_not_invented(self):
        # The rule everywhere in this repo: never invent an identifier or a
        # title. A feature titled with a plausible guess is worse than one
        # saying it does not know.
        out = features.generate(
            _cases("| TC1 | R9 | manual | S | G | W | T | not run |\n"),
            parse.parse_requirements(REQS),
        )
        self.assertIn("(not in requirements.md)", out["r9.feature"])

    def test_one_file_per_requirement(self):
        out = features.generate(
            _cases(
                "| TC1 | R1 | manual | A | G | W | T | not run |\n",
                "| TC2 | R1 | manual | B | G | W | T | not run |\n",
                "| TC3 | N1 | manual | C | G | W | T | not run |\n",
            ),
            parse.parse_requirements(REQS),
        )
        self.assertEqual(sorted(out), ["n1.feature", "r1.feature"])
        self.assertIn("Scenario: A", out["r1.feature"])
        self.assertIn("Scenario: B", out["r1.feature"])


class TestResultsCannotOverclaim(unittest.TestCase):
    """Every case here is a way a runner report could be read as a pass when
    nothing was proved."""

    def _report(self, tag, steps):
        return [{"uri": "f.feature", "name": "F", "elements": [
            {"name": "S", "tags": [{"name": "@" + tag}], "steps": steps}]}]

    def test_all_steps_passed_is_a_pass(self):
        found = features.results_from_report(
            self._report("TC1", [{"result": {"status": "passed"}}] * 3))
        self.assertEqual(found, {"TC1": "pass"})

    def test_any_failed_step_is_a_fail(self):
        found = features.results_from_report(self._report("TC1", [
            {"result": {"status": "passed"}}, {"result": {"status": "failed"}}]))
        self.assertEqual(found, {"TC1": "fail"})

    def test_an_undefined_step_is_not_run_rather_than_pass(self):
        # A step nobody implemented has proved nothing. Cucumber reports the
        # scenario without a failure, which is exactly how this reads as green
        # if you only look for "failed".
        found = features.results_from_report(
            self._report("TC1", [{"result": {"status": "undefined"}}]))
        self.assertEqual(found, {"TC1": "not run"})

    def test_an_empty_scenario_is_not_run_rather_than_pass(self):
        # An empty scenario trivially has no failing step. `all()` over an
        # empty list is True, so the naive implementation calls this a pass.
        found = features.results_from_report(self._report("TC1", []))
        self.assertEqual(found, {"TC1": "not run"})

    def test_a_scenario_without_a_case_tag_is_ignored(self):
        report = [{"uri": "f.feature", "name": "F", "elements": [
            {"name": "S", "tags": [{"name": "@smoke"}],
             "steps": [{"result": {"status": "passed"}}]}]}]
        self.assertEqual(features.results_from_report(report), {})


class TestApplyingResults(unittest.TestCase):
    def test_only_reported_rows_are_touched(self):
        text = HEADER + (
            "| TC1 | R1 | automated | A | G | W | T | not run |\n"
            "| TC2 | R1 | manual | B | G | W | T | not run |\n"
        )
        updated, changed = features.apply_results(text, {"TC1": "pass"})
        self.assertEqual(changed, 1)
        parsed = parse.parse_test_cases(updated)
        by_id = {c.id: c for c in parsed.cases}
        self.assertEqual(by_id["TC1"].result, "pass")
        # A manual case the runner never mentioned keeps its own result. An
        # import must not quietly claim a person ran something.
        self.assertEqual(by_id["TC2"].result, "not run")

    def test_the_rewritten_file_still_parses(self):
        text = HEADER + "| TC1 | R1 | automated | A | G | W | T | not run |\n"
        updated, _ = features.apply_results(text, {"TC1": "fail"})
        parsed = parse.parse_test_cases(updated)
        self.assertEqual(parsed.problems, ())
        self.assertEqual(parsed.cases[0].result, "fail")
        self.assertEqual(parsed.cases[0].mode, "automated")

    def test_an_unknown_result_value_is_never_written(self):
        # apply_results writes whatever the mapper produced; the mapper is the
        # only thing that decides vocabulary. If these ever diverge the file
        # stops parsing, so pin that they agree.
        self.assertTrue(set(features._CUCUMBER_TO_RESULT.values())
                        <= parse.TEST_RESULTS)


class TestGeneratorRefusesBadInput(unittest.TestCase):
    def test_generate_refuses_a_file_with_unreadable_rows(self, ):
        import tempfile, shutil  # noqa: E401
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = Path(tmp)
        (root / "docs" / "engagement").mkdir(parents=True)
        # One good row, one with a bad mode.
        (root / "docs" / "engagement" / "test-cases.md").write_text(
            HEADER
            + "| TC1 | R1 | automated | A | G | W | T | not run |\n"
            + "| TC2 | R1 | sometimes | B | G | W | T | not run |\n"
        )
        # Generating anyway would produce a suite missing TC2 while looking
        # complete — the exact failure the refusal exists to prevent.
        self.assertEqual(features.main(["generate", "--root", str(root),
                                        "--out", str(root / "features")]), 1)
        self.assertFalse((root / "features").exists())


if __name__ == "__main__":
    unittest.main()
