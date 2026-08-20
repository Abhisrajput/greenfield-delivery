import re
import unittest

from dashboard.model import Drift, TaskFile
from dashboard.parse import parse_decisions, parse_tasks

VALID_TASKS = """# Tasks — Northwind

| ID | Task | Req | Owner | Status | Item |
|---|---|---|---|---|---|
| T1 | Add CSV export to the order list | R8 | (unassigned) | done | NWT-104 |
| T2 | Add scheduled export job | R9 | (unassigned) | in-progress | NWT-105 |
| T3 | Add refund endpoint | R9 | (unassigned) | blocked | NWT-106 |
| T4 | Add order list pagination | R7 | (unassigned) | todo | (pending) |
| T5 | Add bulk import | R2 | (unassigned) | dropped | NWT-107 |
"""

EMPTY_TASKS = """# Tasks — Northwind

| ID | Task | Req | Owner | Status | Item |
|---|---|---|---|---|---|
"""

REORDERED_HEADER = """# Tasks — Northwind

| ID | Req | Task | Status | Item |
|---|---|---|---|---|
| T1 | R8 | Add CSV export | (unassigned) | done | NWT-104 |
"""


class TestParseTasks(unittest.TestCase):
    def test_absent_file_is_not_present(self):
        result = parse_tasks(None)
        self.assertIsInstance(result, TaskFile)
        self.assertFalse(result.present)
        self.assertEqual(result.tasks, ())
        self.assertEqual(result.problems, ())

    def test_valid_file_parses_every_row(self):
        result = parse_tasks(VALID_TASKS)
        self.assertTrue(result.present)
        self.assertTrue(result.header_ok)
        self.assertEqual(len(result.tasks), 5)
        self.assertEqual(result.problems, ())

    def test_row_fields_are_read_by_column(self):
        task = parse_tasks(VALID_TASKS).tasks[0]
        self.assertEqual(task.id, "T1")
        self.assertEqual(task.title, "Add CSV export to the order list")
        self.assertEqual(task.req, "R8")
        self.assertEqual(task.status, "done")
        self.assertEqual(task.item, "NWT-104")

    def test_empty_table_is_valid_with_zero_rows(self):
        result = parse_tasks(EMPTY_TASKS)
        self.assertTrue(result.present)
        self.assertTrue(result.header_ok)
        self.assertEqual(result.tasks, ())
        self.assertEqual(result.problems, ())

    def test_reordered_header_is_rejected_not_reinterpreted(self):
        result = parse_tasks(REORDERED_HEADER)
        self.assertTrue(result.present)
        self.assertFalse(result.header_ok)
        self.assertEqual(result.tasks, ())
        self.assertEqual(len(result.problems), 1)
        self.assertIn("header", result.problems[0].message.lower())

    def test_missing_header_is_rejected(self):
        result = parse_tasks("# Tasks — Northwind\n\nNothing here.\n")
        self.assertTrue(result.present)
        self.assertFalse(result.header_ok)
        self.assertEqual(result.tasks, ())
        self.assertEqual(len(result.problems), 1)

    def test_blank_req_is_a_problem_not_none(self):
        text = EMPTY_TASKS + "| T1 | Add export |  | (unassigned) | done | NWT-1 |\n"
        result = parse_tasks(text)
        self.assertEqual(result.tasks, ())
        self.assertEqual(len(result.problems), 1)
        self.assertEqual(result.problems[0].line, 5)
        self.assertIn("Req", result.problems[0].message)

    def test_none_req_is_accepted_verbatim(self):
        text = EMPTY_TASKS + "| T1 | Add export | none | (unassigned) | done | NWT-1 |\n"
        result = parse_tasks(text)
        self.assertEqual(len(result.tasks), 1)
        self.assertEqual(result.tasks[0].req, "none")
        self.assertEqual(result.problems, ())

    def test_unknown_status_is_a_problem(self):
        text = EMPTY_TASKS + "| T1 | Add export | R1 | (unassigned) | almost | NWT-1 |\n"
        result = parse_tasks(text)
        self.assertEqual(result.tasks, ())
        self.assertEqual(len(result.problems), 1)
        self.assertIn("almost", result.problems[0].message)

    def test_wrong_cell_count_is_a_problem(self):
        text = EMPTY_TASKS + "| T1 | Add export | R1 | done |\n"
        result = parse_tasks(text)
        self.assertEqual(result.tasks, ())
        self.assertEqual(len(result.problems), 1)

    def test_good_rows_survive_alongside_bad_ones(self):
        text = (
            EMPTY_TASKS
            + "| T1 | Add export | R1 | (unassigned) | done | NWT-1 |\n"
            + "| T2 | Add import | R2 | (unassigned) | almost | NWT-2 |\n"
            + "| T3 | Add sync | R3 | (unassigned) | todo | (pending) |\n"
        )
        result = parse_tasks(text)
        self.assertEqual([t.id for t in result.tasks], ["T1", "T3"])
        self.assertEqual(len(result.problems), 1)
        self.assertEqual(result.problems[0].line, 6)

    def test_wrong_width_divider_is_a_problem(self):
        text = (
            "# Tasks — Northwind\n"
            "\n"
            "| ID | Task | Req | Owner | Status | Item |\n"
            "|---|---|---|\n"
        )
        result = parse_tasks(text)
        self.assertTrue(result.header_ok)
        self.assertEqual(result.tasks, ())
        self.assertEqual(len(result.problems), 1)
        self.assertEqual(result.problems[0].line, 4)
        self.assertIn("expected 6 cells", result.problems[0].message)

    def test_correct_divider_is_still_skipped_silently(self):
        result = parse_tasks(EMPTY_TASKS)
        self.assertTrue(result.header_ok)
        self.assertEqual(result.tasks, ())
        self.assertEqual(result.problems, ())

    def test_parser_never_raises_on_garbage(self):
        headerless = ["", "|||", "\x00\x01", "| | | | | |", "#" * 5000]
        header = "| ID | Task | Req | Owner | Status | Item |\n|---|---|---|---|---|---|\n"
        pathological_rows = [
            "| " + " | ".join(["x"] * 500) + " |",  # far more cells than header
            "| T1 | \x00\x01 | R1 | (unassigned) | done | NWT-1 |",  # null / control bytes
            "|||||||||||||||||||||||||||||||||||||||",  # only pipes
            "| T1 | Add export | R1 | (unassigned) | done | NWT-1",  # unbalanced pipes (no closing |)
            "| T1 | " + ("x" * 200000) + " | R1 | (unassigned) | done | NWT-1 |",  # very long cell
        ]
        with_header = [header + row for row in pathological_rows]
        for junk in headerless + with_header:
            with self.subTest(junk=junk[:12]):
                result = parse_tasks(junk)
                self.assertIsInstance(result, TaskFile)


from dashboard.model import RequirementsFile  # noqa: E402
from dashboard.parse import parse_requirements  # noqa: E402

VALID_REQS = """# Requirements — Northwind

## Functional

| # | Requirement | Acceptance criterion |
|---|---|---|
| R1 | Customer can place an order | Order appears in the admin list |
| R8 | CSV export of the order list | File downloads with all columns |

## Non-functional

| # | Requirement | Acceptance criterion |
|---|---|---|
| N1 | 99.5% uptime in business hours | Measured monthly |

## Out of scope

| # | Excluded | Note |
|---|---|---|
| X1 | Mobile application | Agreed 2026-07-10 |
"""


class TestParseRequirements(unittest.TestCase):
    def test_absent_file(self):
        result = parse_requirements(None)
        self.assertIsInstance(result, RequirementsFile)
        self.assertFalse(result.present)
        self.assertEqual(result.requirements, ())

    def test_all_three_kinds_are_parsed(self):
        result = parse_requirements(VALID_REQS)
        by_id = {r.id: r for r in result.requirements}
        self.assertEqual(set(by_id), {"R1", "R8", "N1", "X1"})
        self.assertEqual(by_id["R1"].kind, "functional")
        self.assertEqual(by_id["N1"].kind, "non-functional")
        self.assertEqual(by_id["X1"].kind, "out-of-scope")

    def test_text_and_criterion_are_kept(self):
        by_id = {r.id: r for r in parse_requirements(VALID_REQS).requirements}
        self.assertEqual(by_id["R8"].text, "CSV export of the order list")
        self.assertEqual(by_id["R8"].criterion, "File downloads with all columns")

    def test_no_sections_yields_a_problem(self):
        result = parse_requirements("# Requirements\n\nNothing yet.\n")
        self.assertTrue(result.present)
        self.assertEqual(result.requirements, ())
        self.assertEqual(len(result.problems), 1)

    def test_parser_never_raises_on_garbage(self):
        for junk in ["", "## Functional", "|||", "\x00"]:
            with self.subTest(junk=junk[:12]):
                self.assertIsInstance(parse_requirements(junk), RequirementsFile)

    def test_valid_file_has_zero_problems(self):
        result = parse_requirements(VALID_REQS)
        self.assertEqual(result.problems, ())

    def test_two_cell_row_is_a_problem(self):
        text = "# Requirements\n\n## Functional\n\n| R1 | Customer can place an order |\n"
        result = parse_requirements(text)
        self.assertEqual(result.requirements, ())
        self.assertEqual(len(result.problems), 1)
        self.assertEqual(result.problems[0].line, 5)
        self.assertIn("expected 3 cells, found 2", result.problems[0].message)

    def test_four_cell_row_is_a_problem(self):
        text = (
            "# Requirements\n"
            "\n"
            "## Functional\n"
            "\n"
            "| R1 | Customer can place an order | Order appears | extra |\n"
        )
        result = parse_requirements(text)
        self.assertEqual(result.requirements, ())
        self.assertEqual(len(result.problems), 1)
        self.assertEqual(result.problems[0].line, 5)
        self.assertIn("expected 3 cells, found 4", result.problems[0].message)

    def test_prose_under_section_is_not_a_problem(self):
        text = "# Requirements\n\n## Functional\n\nThis is just a sentence, not a table.\n"
        result = parse_requirements(text)
        self.assertEqual(result.requirements, ())
        self.assertEqual(result.problems, ())

    def test_blank_line_under_section_is_not_a_problem(self):
        text = "# Requirements\n\n## Functional\n\n\n"
        result = parse_requirements(text)
        self.assertEqual(result.requirements, ())
        self.assertEqual(result.problems, ())


from dashboard.model import EngagementFile, SignoffFile  # noqa: E402
from dashboard.parse import parse_engagement, parse_signoffs  # noqa: E402

VALID_ENGAGEMENT = """# Engagement: Northwind Trading

- **Started:** 2026-07-06
- **Shape:** Fixed-scope greenfield MVP, 6 weeks

## Tracker
- type: jira
- site: northwind.atlassian.net
- project: NWT
- epic: NWT-142

## Progress reporting
- narrative: confluence
- space: NWT
- page: Delivery Status
- dashboard: (pending)
"""

VALID_SIGNOFFS = """# Sign-offs

| Gate | Artifact | Commit | Approved by | Date | Evidence |
|---|---|---|---|---|---|
| Requirements | requirements.md | a1b2c3d | Jane Doe, CTO | 2026-07-17 | https://slack/1 |
| Design | design.md | 9e04f77 | Jane Doe, CTO | 2026-07-29 | https://slack/2 |
"""


class TestRequirementsHeaderRow(unittest.TestCase):
    def test_section_header_row_is_not_parsed_as_a_requirement(self):
        # A well-formed requirements.md with three sections was yielding three
        # phantom requirements whose id was literally "ID" — the header rows.
        # `_is_divider` caught the |---| line beneath each one, but "ID" starts
        # with a letter so the header itself was admitted. Each phantom had no
        # tasks pointing at it, so the dashboard reported CRITICAL "ID has no
        # tasks — unplanned work" against a file containing no defects.
        text = """# Requirements

## Functional

| ID | Requirement | Acceptance criteria |
|---|---|---|
| R1 | Something | It does the thing |

## Non-functional

| ID | Requirement | Acceptance criteria |
|---|---|---|
| N1 | Fast enough | Under 200ms |

## Out of scope

| ID | Item | Note |
|---|---|---|
| X1 | Not this | Next quarter |
"""
        parsed = parse_requirements(text)
        self.assertEqual([r.id for r in parsed.requirements], ["R1", "N1", "X1"])
        self.assertNotIn("ID", [r.id for r in parsed.requirements])
        self.assertEqual(parsed.problems, ())


class TestParseEngagement(unittest.TestCase):
    def test_absent_file(self):
        result = parse_engagement(None)
        self.assertIsInstance(result, EngagementFile)
        self.assertFalse(result.present)
        self.assertIsNone(result.engagement)

    def test_reads_client_and_blocks(self):
        engagement = parse_engagement(VALID_ENGAGEMENT).engagement
        self.assertEqual(engagement.client, "Northwind Trading")
        self.assertEqual(engagement.tracker_type, "jira")
        self.assertEqual(engagement.project, "NWT")
        self.assertEqual(engagement.epic, "NWT-142")
        self.assertEqual(engagement.narrative, "confluence")

    def test_pending_is_preserved_verbatim(self):
        engagement = parse_engagement(VALID_ENGAGEMENT).engagement
        self.assertEqual(engagement.dashboard_url, "(pending)")

    def test_missing_blocks_are_each_a_problem(self):
        result = parse_engagement("# Engagement: Acme\n")
        self.assertTrue(result.present)
        messages = [p.message for p in result.problems]
        self.assertEqual(len(messages), 2)
        self.assertTrue(any("Tracker" in m for m in messages))
        self.assertTrue(any("Progress reporting" in m for m in messages))

    def test_missing_epic_inside_an_existing_tracker_block_is_a_problem(self):
        # Deferred-5: a `## Tracker` block with no `epic:` line used to yield
        # epic='' with no Problem at all, silently disabling the "tasks not
        # yet in the tracker" check downstream (it is gated on `epic` being
        # set — see analyse.findings).
        text = (
            "# Engagement: Acme\n\n"
            "## Tracker\n"
            "- type: jira\n"
            "- project: ACME\n\n"
            "## Progress reporting\n"
            "- narrative: confluence\n"
        )
        result = parse_engagement(text)
        self.assertEqual(result.engagement.epic, "")
        messages = [p.message for p in result.problems]
        self.assertEqual(len(messages), 1)
        self.assertIn("epic", messages[0])

    def test_missing_narrative_inside_an_existing_reporting_block_is_a_problem(self):
        # Same defect for `narrative:`, which gates the staleness check.
        text = (
            "# Engagement: Acme\n\n"
            "## Tracker\n"
            "- type: jira\n"
            "- project: ACME\n"
            "- epic: ACME-1\n\n"
            "## Progress reporting\n"
            "- space: ACME\n"
        )
        result = parse_engagement(text)
        self.assertEqual(result.engagement.narrative, "")
        messages = [p.message for p in result.problems]
        self.assertEqual(len(messages), 1)
        self.assertIn("narrative", messages[0])

    def test_present_epic_and_narrative_produce_no_problem(self):
        result = parse_engagement(VALID_ENGAGEMENT)
        self.assertEqual(result.problems, ())

    def test_parser_never_raises_on_garbage(self):
        headerless = ["", "|||", "\x00\x01", "# Engagement:", "#" * 5000]
        header = "# Engagement: Northwind\n\n## Tracker\n"
        pathological_rows = [
            "- " + " | ".join(["x"] * 500) + ": value",  # far more cells than expected
            "- key: \x00\x01",  # null / control bytes
            "-|||||||||||||||||||||||||||||||||||||||",  # only pipes
            "- key",  # unbalanced — no colon
            "- key: " + ("x" * 200000),  # very long value
        ]
        with_header = [header + row for row in pathological_rows]
        for junk in headerless + with_header:
            with self.subTest(junk=junk[:12]):
                result = parse_engagement(junk)
                self.assertIsInstance(result, EngagementFile)


class TestParseSignoffs(unittest.TestCase):
    def test_absent_file(self):
        result = parse_signoffs(None)
        self.assertIsInstance(result, SignoffFile)
        self.assertFalse(result.present)

    def test_rows_parse_with_commit_column(self):
        result = parse_signoffs(VALID_SIGNOFFS)
        self.assertTrue(result.header_ok)
        self.assertEqual(len(result.signoffs), 2)
        self.assertEqual(result.signoffs[0].gate, "Requirements")
        self.assertEqual(result.signoffs[0].artifact, "requirements.md")
        self.assertEqual(result.signoffs[0].commit, "a1b2c3d")
        self.assertEqual(result.signoffs[1].date, "2026-07-29")

    def test_old_five_column_format_is_rejected_not_shifted(self):
        old = """# Sign-offs

| Gate | Artifact | Approved by | Date | Evidence |
|---|---|---|---|---|
| Requirements | requirements.md | Jane | 2026-07-17 | https://slack/1 |
"""
        result = parse_signoffs(old)
        self.assertFalse(result.header_ok)
        self.assertEqual(result.signoffs, ())
        self.assertEqual(len(result.problems), 1)

    def test_blank_commit_is_a_problem(self):
        text = VALID_SIGNOFFS + "| Build | tasks.md |  | Jane | 2026-08-01 | x |\n"
        result = parse_signoffs(text)
        self.assertEqual(len(result.signoffs), 2)
        self.assertEqual(len(result.problems), 1)
        self.assertIn("Commit", result.problems[0].message)

    def test_wrong_width_divider_is_a_problem(self):
        text = (
            "# Sign-offs\n"
            "\n"
            "| Gate | Artifact | Commit | Approved by | Date | Evidence |\n"
            "|---|---|---|\n"
        )
        result = parse_signoffs(text)
        self.assertTrue(result.header_ok)
        self.assertEqual(result.signoffs, ())
        self.assertEqual(len(result.problems), 1)
        self.assertEqual(result.problems[0].line, 4)
        self.assertIn("expected 6 cells", result.problems[0].message)

    def test_correct_divider_is_still_skipped_silently(self):
        text = (
            "# Sign-offs\n"
            "\n"
            "| Gate | Artifact | Commit | Approved by | Date | Evidence |\n"
            "|---|---|---|---|---|---|\n"
        )
        result = parse_signoffs(text)
        self.assertTrue(result.header_ok)
        self.assertEqual(result.signoffs, ())
        self.assertEqual(result.problems, ())

    def test_parser_never_raises_on_garbage(self):
        headerless = ["", "|||", "\x00\x01", "| | | | | | |", "#" * 5000]
        header = (
            "| Gate | Artifact | Commit | Approved by | Date | Evidence |\n"
            "|---|---|---|---|---|---|\n"
        )
        pathological_rows = [
            "| " + " | ".join(["x"] * 500) + " |",  # far more cells than header
            "| Build | tasks.md | \x00\x01 | Jane | 2026-08-01 | x |",  # control bytes
            "|||||||||||||||||||||||||||||||||||||||",  # only pipes
            "| Build | tasks.md | abc123 | Jane | 2026-08-01 | x",  # unbalanced pipes
            "| Build | tasks.md | " + ("x" * 200000) + " | Jane | 2026-08-01 | x |",  # long cell
        ]
        with_header = [header + row for row in pathological_rows]
        for junk in headerless + with_header:
            with self.subTest(junk=junk[:12]):
                result = parse_signoffs(junk)
                self.assertIsInstance(result, SignoffFile)


from dashboard import analyse  # noqa: E402


def _tasks(*rows: str):
    return parse_tasks(EMPTY_TASKS + "".join(rows))


class TestCounts(unittest.TestCase):
    def test_counts_each_status(self):
        counts = analyse.count(parse_tasks(VALID_TASKS).tasks)
        self.assertEqual(counts.done, 1)
        self.assertEqual(counts.in_progress, 1)
        self.assertEqual(counts.blocked, 1)
        self.assertEqual(counts.todo, 1)
        self.assertEqual(counts.dropped, 1)

    def test_dropped_is_excluded_from_the_denominator(self):
        counts = analyse.count(parse_tasks(VALID_TASKS).tasks)
        self.assertEqual(counts.total_active, 4)

    def test_remaining_is_everything_not_done_or_dropped(self):
        counts = analyse.count(parse_tasks(VALID_TASKS).tasks)
        self.assertEqual(counts.remaining, 3)

    def test_empty_task_list_counts_zero_without_error(self):
        counts = analyse.count(())
        self.assertEqual(counts.total_active, 0)
        self.assertEqual(counts.remaining, 0)


class TestCoverage(unittest.TestCase):
    def test_out_of_scope_entries_are_not_coverage_rows(self):
        rows = analyse.coverage(parse_requirements(VALID_REQS), _tasks())
        self.assertEqual([row.requirement.id for row in rows], ["R1", "R8", "N1"])

    def test_requirement_with_no_tasks_has_empty_task_tuple(self):
        rows = analyse.coverage(parse_requirements(VALID_REQS), _tasks())
        self.assertTrue(all(row.tasks == () for row in rows))

    def test_tasks_attach_to_their_requirement(self):
        tasks = _tasks(
            "| T1 | Add export | R8 | (unassigned) | done | NWT-1 |\n",
            "| T2 | Add columns | R8 | (unassigned) | todo | NWT-2 |\n",
        )
        rows = {row.requirement.id: row for row in analyse.coverage(parse_requirements(VALID_REQS), tasks)}
        self.assertEqual(len(rows["R8"].tasks), 2)
        self.assertEqual(rows["R8"].counts.done, 1)
        self.assertEqual(rows["R1"].tasks, ())

    def test_unlinked_tasks_are_found(self):
        tasks = _tasks(
            "| T1 | Add export | none | (unassigned) | done | NWT-1 |\n",
            "| T2 | Add columns | R8 | (unassigned) | todo | NWT-2 |\n",
        )
        self.assertEqual([t.id for t in analyse.unlinked(tasks)], ["T1"])

    def test_tasks_citing_out_of_scope_are_found(self):
        tasks = _tasks("| T1 | Build the app | X1 | (unassigned) | todo | NWT-1 |\n")
        found = analyse.out_of_scope_tasks(parse_requirements(VALID_REQS), tasks)
        self.assertEqual([t.id for t in found], ["T1"])

    def test_dangling_references_are_found(self):
        tasks = _tasks("| T1 | Add export | R99 | (unassigned) | todo | NWT-1 |\n")
        found = analyse.dangling(parse_requirements(VALID_REQS), tasks)
        self.assertEqual([t.id for t in found], ["T1"])

    def test_none_is_not_dangling(self):
        tasks = _tasks("| T1 | Add export | none | (unassigned) | todo | NWT-1 |\n")
        self.assertEqual(analyse.dangling(parse_requirements(VALID_REQS), tasks), ())

    def test_no_requirements_file_yields_no_coverage_rows(self):
        self.assertEqual(analyse.coverage(parse_requirements(None), _tasks()), ())

    def test_unreadable_tasks_file_yields_no_coverage_rows(self):
        # C2: coverage() must not compute from tasks.tasks (== ()) when the
        # file is present but unreadable — that would draw a confident "no
        # tasks" for every requirement from a file the parser refused to
        # read, rather than a "cannot compute" state.
        unreadable = parse_tasks(REORDERED_HEADER)
        self.assertFalse(unreadable.header_ok)
        self.assertEqual(analyse.coverage(parse_requirements(VALID_REQS), unreadable), ())

    def test_unreadable_tasks_file_yields_no_unplanned_work_findings(self):
        unreadable = parse_tasks(REORDERED_HEADER)
        found = analyse.findings(
            engagement=parse_engagement(VALID_ENGAGEMENT),
            reqs=parse_requirements(VALID_REQS),
            tasks=unreadable,
            signoffs=parse_signoffs(VALID_SIGNOFFS),
            signoff_status={
                ("a1b2c3d", "requirements.md"): "unchanged",
                ("9e04f77", "design.md"): "unchanged",
            },
            status_age_days=None,
            cadence_days=7,
        )
        self.assertFalse(any("has no tasks" in f.detail for f in found))
        self.assertFalse(any("unplanned work" in f.detail for f in found))


import subprocess  # noqa: E402
import tempfile  # noqa: E402
import unittest.mock  # noqa: E402
from pathlib import Path  # noqa: E402

from dashboard import history  # noqa: E402


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


class TestHistory(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "t@example.com")
        _git(self.root, "config", "user.name", "Test")
        (self.root / "docs").mkdir()
        self.rel = "docs/tasks.md"
        (self.root / self.rel).write_text("one\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "first")
        self.first = _git(self.root, "rev-parse", "HEAD")

    def tearDown(self):
        self._tmp.cleanup()

    def test_is_repo(self):
        self.assertTrue(history.is_repo(self.root))

    def test_non_repo_is_detected(self):
        with tempfile.TemporaryDirectory() as plain:
            self.assertFalse(history.is_repo(Path(plain)))

    def test_unchanged_artifact(self):
        self.assertEqual(
            history.artifact_status(self.root, self.first, self.rel), "unchanged"
        )

    def test_changed_artifact(self):
        (self.root / self.rel).write_text("two\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "second")
        self.assertEqual(
            history.artifact_status(self.root, self.first, self.rel), "changed"
        )

    def test_path_absent_at_approved_commit_is_unverifiable_not_unchanged(self):
        # Regression guard: `git diff --quiet` exits 0 for a path that has
        # never existed (no differences in an empty path set), which the old
        # code mapped straight to "unchanged" — a false green tick on an
        # approval that was never actually checked against anything.
        self.assertEqual(
            history.artifact_status(self.root, self.first, "docs/never-existed.md"),
            "unverifiable",
        )

    def test_artifact_present_at_approval_then_deleted_is_changed(self):
        (self.root / self.rel).unlink()
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "delete")
        self.assertEqual(
            history.artifact_status(self.root, self.first, self.rel), "changed"
        )

    def test_unknown_commit_is_unverifiable_not_unchanged(self):
        self.assertEqual(
            history.artifact_status(self.root, "0" * 40, self.rel), "unverifiable"
        )

    def test_garbage_commit_is_unverifiable(self):
        for bad in ["", "not-a-sha", "--upload-pack=evil", "HEAD~999"]:
            with self.subTest(bad=bad):
                self.assertEqual(
                    history.artifact_status(self.root, bad, self.rel), "unverifiable"
                )

    def test_revisions_are_oldest_first_with_content(self):
        (self.root / self.rel).write_text("two\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "second")
        ok, revisions = history.revisions(self.root, self.rel)
        self.assertTrue(ok)
        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[0][1], "one\n")
        self.assertEqual(revisions[1][1], "two\n")
        self.assertLessEqual(revisions[0][0], revisions[1][0])

    def test_revisions_of_untracked_path_is_empty(self):
        # git itself ran fine; it simply found no history for this path —
        # distinct from git failing to run at all (ok=False), covered below.
        self.assertEqual(history.revisions(self.root, "docs/nope.md"), (True, ()))

    def test_revisions_in_non_repo_signals_failure_not_empty(self):
        with tempfile.TemporaryDirectory() as plain:
            self.assertEqual(history.revisions(Path(plain), self.rel), (False, ()))

    def test_revisions_count_matches_commits_touching_path(self):
        # Forces one blob read to fail so an unreadable revision is actually
        # present in the fixture. Without that, every revision here is a
        # readable blob and this equality would hold identically whether or
        # not revisions() silently dropped unreadable ones — it would prove
        # nothing about that failure mode. With the forced failure, a future
        # silent drop (skipping the unreadable revision instead of returning
        # it with empty content) would shrink len(revisions) below
        # commit_count, and this would fail.
        (self.root / self.rel).write_text("two\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "second")
        (self.root / self.rel).write_text("three\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "third")
        commit_count = int(
            _git(self.root, "rev-list", "--count", "HEAD", "--", self.rel)
        )

        real_run = history._run
        calls = {"show": 0}

        def fake_run(root, *args):
            if args and args[0] == "show":
                calls["show"] += 1
                if calls["show"] == 2:
                    return subprocess.CompletedProcess(args, returncode=128, stdout="")
            return real_run(root, *args)

        with unittest.mock.patch.object(history, "_run", side_effect=fake_run):
            ok, revisions = history.revisions(self.root, self.rel)

        self.assertTrue(ok)
        self.assertEqual(len(revisions), commit_count)
        self.assertEqual(sum(1 for _, content in revisions if content == ""), 1)

    def test_unreadable_blob_is_returned_with_empty_content_not_dropped(self):
        # Constructing a genuinely unreadable blob (e.g. a directory where the
        # path used to be a file) is not reliable: `git show <sha>:<path>` on
        # a directory succeeds (returncode 0) and prints a tree listing
        # rather than failing, at least on the macOS git used here. So this
        # forces the failure directly at the subprocess boundary instead,
        # which is the same contract `revisions()` checks (blob is None or
        # blob.returncode != 0), to prove the revision is appended with
        # empty content rather than skipped.
        (self.root / self.rel).write_text("two\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "second")

        # The real commit timestamps, oldest first, straight from git — the
        # same ordering and format (%cI) that history.revisions() itself
        # parses out of "git log --format=%H %cI --reverse". Comparing
        # against these exact values (rather than merely asserting
        # non-empty and non-decreasing) means a wrong, empty, or reordered
        # date fails this test, not just a garbage-but-plausible string.
        expected_dates = _git(
            self.root, "log", "--format=%cI", "--reverse", "--", self.rel
        ).splitlines()

        real_run = history._run

        def fake_run(root, *args):
            if args and args[0] == "show":
                return subprocess.CompletedProcess(args, returncode=128, stdout="")
            return real_run(root, *args)

        with unittest.mock.patch.object(history, "_run", side_effect=fake_run):
            ok, revisions = history.revisions(self.root, self.rel)

        self.assertTrue(ok)
        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[0][1], "")
        self.assertEqual(revisions[1][1], "")
        self.assertEqual([rev[0] for rev in revisions], expected_dates)

    def test_revisions_signals_failure_when_git_log_itself_fails(self):
        # Simulates a git-log failure (corrupt object store, permissions,
        # timeout) rather than "no history for this path" — the two must not
        # collapse to the same `()` result, or the renderer would assert a
        # false "no committed history yet" when it actually could not check.
        real_run = history._run

        def fake_run(root, *args):
            if args and args[0] == "log":
                return subprocess.CompletedProcess(args, returncode=128, stdout="")
            return real_run(root, *args)

        with unittest.mock.patch.object(history, "_run", side_effect=fake_run):
            ok, revisions = history.revisions(self.root, self.rel)

        self.assertFalse(ok)
        self.assertEqual(revisions, ())


class TestEngagementCommits(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "t@example.com")
        _git(self.root, "config", "user.name", "Test")
        (self.root / "docs" / "engagement").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _commit(self, name, text, message):
        (self.root / "docs" / "engagement" / name).write_text(text)
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", message)

    def test_lists_only_commits_touching_the_engagement(self):
        self._commit("tasks.md", "one\n", "first")
        (self.root / "unrelated.txt").write_text("x")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "unrelated")
        ok, commits = history.engagement_commits(self.root)
        self.assertTrue(ok)
        self.assertEqual(len(commits), 1)

    def test_reports_which_files_changed(self):
        self._commit("tasks.md", "one\n", "first")
        ok, commits = history.engagement_commits(self.root)
        self.assertIn("docs/engagement/tasks.md", commits[0][2])

    def test_reports_multiple_files_changed_in_one_commit(self):
        self._commit("tasks.md", "one\n", "first")
        (self.root / "docs" / "engagement" / "tasks.md").write_text("two\n")
        (self.root / "docs" / "engagement" / "reqs.md").write_text("three\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "second")
        ok, commits = history.engagement_commits(self.root)
        self.assertTrue(ok)
        self.assertEqual(len(commits), 2)
        self.assertEqual(
            set(commits[1][2]),
            {"docs/engagement/tasks.md", "docs/engagement/reqs.md"},
        )

    def test_single_commit_touching_engagement_and_unrelated_reports_only_engagement(self):
        # A single commit that touches both a docs/engagement/ file and an
        # unrelated file at once — the brief called this case out explicitly,
        # and it was previously untested even though the filtering looked
        # correct by inspection.
        (self.root / "docs" / "engagement" / "tasks.md").write_text("one\n")
        (self.root / "unrelated.txt").write_text("x")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "mixed")
        ok, commits = history.engagement_commits(self.root)
        self.assertTrue(ok)
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0][2], ("docs/engagement/tasks.md",))

    def test_merge_commit_reports_first_parent_diff(self):
        # --name-only prints no path lines for a merge commit by default, so
        # a merge that brings in engagement changes would otherwise
        # contribute nothing to the feed — silently under-reporting on any
        # repo that merges via pull requests. --diff-merges=first-parent
        # makes the merge commit report its net change against main.
        self._commit("tasks.md", "one\n", "first")
        _git(self.root, "checkout", "-q", "-b", "feature")
        self._commit("tasks.md", "two\n", "on-branch")
        _git(self.root, "checkout", "-q", "main")
        _git(self.root, "merge", "--no-ff", "-q", "-m", "merge feature", "feature")
        merge_sha = _git(self.root, "rev-parse", "HEAD")

        ok, commits = history.engagement_commits(self.root)
        self.assertTrue(ok)
        by_sha = {sha: paths for sha, _when, paths in commits}
        self.assertIn(merge_sha, by_sha)
        self.assertIn("docs/engagement/tasks.md", by_sha[merge_sha])

    def test_oldest_first(self):
        self._commit("tasks.md", "one\n", "first")
        self._commit("tasks.md", "two\n", "second")
        ok, commits = history.engagement_commits(self.root)
        self.assertLessEqual(commits[0][1], commits[1][1])

    def test_non_repo_signals_failure_not_empty(self):
        with tempfile.TemporaryDirectory() as plain:
            ok, commits = history.engagement_commits(Path(plain))
            self.assertFalse(ok)
            self.assertEqual(commits, ())

    def test_no_engagement_history_is_ok_with_empty_commits(self):
        # git ran fine; there just are no commits touching docs/engagement/ —
        # distinct from git failing to run at all (ok=False), covered above.
        (self.root / "unrelated.txt").write_text("x")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "unrelated")
        ok, commits = history.engagement_commits(self.root)
        self.assertTrue(ok)
        self.assertEqual(commits, ())

    def test_file_at_returns_content_when_present(self):
        self._commit("tasks.md", "one\n", "first")
        ok, commits = history.engagement_commits(self.root)
        sha = commits[0][0]
        self.assertEqual(
            history.file_at(self.root, sha, "docs/engagement/tasks.md"),
            (True, "one\n"),
        )

    def test_file_at_returns_ok_true_none_when_genuinely_absent(self):
        # The path was not in the tree at that commit. That is a real
        # answer, distinct from git failing to read anything at all.
        self._commit("tasks.md", "one\n", "first")
        ok, commits = history.engagement_commits(self.root)
        sha = commits[0][0]
        self.assertEqual(
            history.file_at(self.root, sha, "docs/engagement/nope.md"),
            (True, None),
        )

    def test_file_at_signals_failure_when_git_show_fails_after_existence_check_passes(self):
        # git says the path exists at this commit, but reading the blob
        # itself fails — a genuine git failure, not an absence. Must be
        # reported as ok=False, never conflated with "not there".
        self._commit("tasks.md", "one\n", "first")
        ok, commits = history.engagement_commits(self.root)
        sha = commits[0][0]

        real_run = history._run

        def fake_run(root, *args):
            if args and args[0] == "show":
                return subprocess.CompletedProcess(args, returncode=128, stdout="")
            return real_run(root, *args)

        with unittest.mock.patch.object(history, "_run", side_effect=fake_run):
            self.assertEqual(
                history.file_at(self.root, sha, "docs/engagement/tasks.md"),
                (False, None),
            )

    def test_file_at_signals_failure_when_git_cannot_be_read(self):
        # git itself cannot be read at all (e.g. root is not a repository).
        # This must read as "cannot tell" (ok=False), never as "the file
        # was absent" (which would be ok=True, content=None) — the two are
        # different claims and callers must be able to tell them apart.
        self._commit("tasks.md", "one\n", "first")
        ok, commits = history.engagement_commits(self.root)
        sha = commits[0][0]
        with tempfile.TemporaryDirectory() as plain:
            self.assertEqual(
                history.file_at(Path(plain), sha, "docs/engagement/tasks.md"),
                (False, None),
            )


class TestFindings(unittest.TestCase):
    def _call(self, **overrides):
        kwargs = dict(
            engagement=parse_engagement(VALID_ENGAGEMENT),
            reqs=parse_requirements(VALID_REQS),
            tasks=_tasks(),
            signoffs=parse_signoffs(VALID_SIGNOFFS),
            signoff_status={
                ("a1b2c3d", "requirements.md"): "unchanged",
                ("9e04f77", "design.md"): "unchanged",
            },
            status_age_days=None,
            cadence_days=7,
        )
        kwargs.update(overrides)
        return analyse.findings(**kwargs)

    def test_two_signoffs_at_the_same_commit_are_verified_independently(self):
        # C1: `commands/gate.md` legitimately commits several artifacts at
        # one SHA and signs each off in its own row. Keying signoff_status by
        # commit alone would let one artifact's "unchanged" status silently
        # cover another's — a green tick with no finding for a file that
        # provably changed. Keying by (commit, artifact) must not do that.
        signoffs = parse_signoffs(
            "# Sign-offs\n\n"
            "| Gate | Artifact | Commit | Approved by | Date | Evidence |\n"
            "|---|---|---|---|---|---|\n"
            "| Discovery | discovery.md | 3bdbf6b | Jane Doe | 2026-07-17 | x |\n"
            "| Requirements | requirements.md | 3bdbf6b | Jane Doe | 2026-07-17 | x |\n"
        )
        found = self._call(
            signoffs=signoffs,
            signoff_status={
                ("3bdbf6b", "discovery.md"): "unchanged",
                ("3bdbf6b", "requirements.md"): "changed",
            },
        )
        changed = [f for f in found if "requirements.md" in f.detail]
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0].severity, "critical")
        self.assertFalse(any("discovery.md" in f.detail for f in found))

    def test_changed_artifact_is_critical(self):
        found = self._call(signoff_status={
            ("a1b2c3d", "requirements.md"): "unchanged",
            ("9e04f77", "design.md"): "changed",
        })
        matching = [f for f in found if "design.md" in f.detail]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].severity, "critical")

    def test_unverifiable_signoff_is_critical_and_says_so(self):
        found = self._call(signoff_status={
            ("a1b2c3d", "requirements.md"): "unverifiable",
            ("9e04f77", "design.md"): "unchanged",
        })
        matching = [f for f in found if "a1b2c3d" in f.detail]
        self.assertEqual(matching[0].severity, "critical")
        self.assertIn("cannot verify", matching[0].detail.lower())

    def test_uncovered_requirement_is_critical(self):
        # Partially covered: R8 and N1 have tasks, R1 has none. The fixture must
        # NOT be an empty task list — that is a different fact with its own
        # finding (below), and using it here conflated "this requirement is
        # uncovered" with "no tasks exist yet".
        tasks = _tasks(
            "| T1 | Add export | R8 | (unassigned) | done | NWT-1 |\n",
            "| T2 | Add uptime check | N1 | (unassigned) | todo | NWT-2 |\n",
        )
        found = self._call(tasks=tasks)
        self.assertTrue(any(f.severity == "critical" and "R1" in f.detail for f in found))

    def test_empty_task_list_after_design_signoff_is_one_finding_not_one_each(self):
        # Design is signed off in VALID_SIGNOFFS, so tasks should exist. An
        # empty file is a single problem, not one problem per requirement.
        found = self._call()
        self.assertEqual([f for f in found if "has no tasks" in f.detail], [])
        matching = [f for f in found if f.label == "Task list is empty"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].severity, "critical")

    def test_no_coverage_findings_before_the_design_gate(self):
        # tasks.md is produced at gate 2. Before Design is signed off every
        # requirement legitimately has no tasks, and reporting each as
        # unplanned work would fill the panel with false criticals on day one.
        before_design = parse_signoffs(
            "# Sign-offs\n\n"
            "| Gate | Artifact | Commit | Approved by | Date | Evidence |\n"
            "|---|---|---|---|---|---|\n"
            "| Requirements | requirements.md | a1b2c3d | Jane | 2026-07-17 | x |\n"
        )
        found = self._call(
            signoffs=before_design,
            signoff_status={("a1b2c3d", "requirements.md"): "unchanged"},
        )
        self.assertFalse(any("has no tasks" in f.detail for f in found))
        self.assertFalse(any(f.label == "Task list is empty" for f in found))

    def test_out_of_scope_task_is_critical(self):
        found = self._call(tasks=_tasks("| T1 | Build app | X1 | (unassigned) | todo | NWT-1 |\n"))
        self.assertTrue(
            any(f.severity == "critical" and "X1" in f.detail for f in found)
        )

    def test_unlinked_task_is_serious(self):
        tasks = _tasks(
            "| T1 | Add export | none | (unassigned) | todo | NWT-1 |\n",
            "| T2 | Add order | R1 | (unassigned) | done | NWT-2 |\n",
            "| T3 | Add export | R8 | (unassigned) | done | NWT-3 |\n",
            "| T4 | Add uptime | N1 | (unassigned) | done | NWT-4 |\n",
        )
        found = [f for f in self._call(tasks=tasks) if "T1" in f.detail]
        self.assertEqual(found[0].severity, "serious")

    def test_blocked_task_is_serious(self):
        tasks = _tasks("| T1 | Add export | R8 | (unassigned) | blocked | NWT-1 |\n")
        self.assertTrue(any(f.severity == "serious" and "blocked" in f.label.lower()
                            for f in self._call(tasks=tasks)))

    def test_pending_item_with_epic_set_is_a_warning(self):
        tasks = _tasks("| T1 | Add export | R8 | (unassigned) | todo | (pending) |\n")
        self.assertTrue(any(f.severity == "warning" and "tracker" in f.detail.lower()
                            for f in self._call(tasks=tasks)))

    def test_status_page_not_visible_locally_is_not_reported_stale(self):
        found = self._call(status_age_days=None)
        self.assertFalse(any("stale" in f.detail.lower() for f in found))

    def test_status_page_older_than_cadence_is_a_warning(self):
        found = [f for f in self._call(status_age_days=9) if "status" in f.detail.lower()]
        self.assertEqual(found[0].severity, "warning")

    def test_parse_problems_become_warnings_naming_the_line(self):
        tasks = _tasks("| T1 | Add export | R8 | (unassigned) | almost | NWT-1 |\n")
        found = [f for f in self._call(tasks=tasks) if "line 5" in f.detail]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, "warning")

    def test_findings_are_returned_in_severity_order(self):
        from dashboard.model import SEVERITY_ORDER

        found = self._call(
            tasks=_tasks("| T1 | Add export | none | (unassigned) | blocked | (pending) |\n"),
            signoff_status={
                ("a1b2c3d", "requirements.md"): "changed",
                ("9e04f77", "design.md"): "unchanged",
            },
        )
        ranks = [SEVERITY_ORDER.index(f.severity) for f in found]
        self.assertEqual(ranks, sorted(ranks))


class TestTrend(unittest.TestCase):
    def _revision(self, *rows: str) -> str:
        return EMPTY_TASKS + "".join(rows)

    def test_each_revision_becomes_a_point(self):
        revisions = (
            ("2026-07-29T10:00:00+00:00", self._revision("| T1 | A | R1 | (unassigned) | todo | x |\n")),
            ("2026-08-01T10:00:00+00:00", self._revision("| T1 | A | R1 | (unassigned) | done | x |\n")),
        )
        result = analyse.trend(True, revisions)
        self.assertEqual([p.remaining for p in result.points], [1, 0])
        self.assertEqual(result.readable, 2)
        self.assertEqual(result.unreadable, 0)
        self.assertTrue(result.history_ok)

    def test_unreadable_revision_is_a_gap_not_interpolated(self):
        revisions = (
            ("2026-07-29T10:00:00+00:00", self._revision("| T1 | A | R1 | (unassigned) | todo | x |\n")),
            ("2026-08-01T10:00:00+00:00", "garbage with no table"),
            ("2026-08-03T10:00:00+00:00", self._revision("| T1 | A | R1 | (unassigned) | done | x |\n")),
        )
        result = analyse.trend(True, revisions)
        self.assertEqual([p.readable for p in result.points], [True, False, True])
        self.assertIsNone(result.points[1].remaining)
        self.assertEqual(result.readable, 2)
        self.assertEqual(result.unreadable, 1)

    def test_dropped_tasks_leave_the_remaining_count(self):
        revisions = (
            ("2026-07-29T10:00:00+00:00", self._revision(
                "| T1 | A | R1 | (unassigned) | todo | x |\n", "| T2 | B | R1 | (unassigned) | todo | y |\n")),
            ("2026-08-01T10:00:00+00:00", self._revision(
                "| T1 | A | R1 | (unassigned) | todo | x |\n", "| T2 | B | R1 | (unassigned) | dropped | y |\n")),
        )
        result = analyse.trend(True, revisions)
        self.assertEqual([p.remaining for p in result.points], [2, 1])

    def test_no_revisions_is_an_empty_trend(self):
        result = analyse.trend(True, ())
        self.assertEqual(result.points, ())
        self.assertEqual(result.readable, 0)

    def test_history_not_ok_is_carried_onto_the_trend(self):
        # git itself failed to be read (corrupt object store, timeout, ...);
        # distinct from "read git fine, no history" (empty revisions with
        # history_ok=True, covered above).
        result = analyse.trend(False, ())
        self.assertFalse(result.history_ok)
        self.assertEqual(result.points, ())


from dashboard import render  # noqa: E402
from dashboard.model import Event, Feed, Gate, State  # noqa: E402


def _state(**overrides):
    tasks = overrides.pop("tasks", _tasks())
    reqs = overrides.pop("reqs", parse_requirements(VALID_REQS))
    base = dict(
        engagement=parse_engagement(VALID_ENGAGEMENT),
        reqs=reqs,
        tasks=tasks,
        signoffs=parse_signoffs(VALID_SIGNOFFS),
        signoff_status={
            ("a1b2c3d", "requirements.md"): "unchanged",
            ("9e04f77", "design.md"): "unchanged",
        },
        findings=(),
        trend=analyse.trend(True, ()),
        gates=(
            Gate("Discovery", "discovery.md", "pending", "", ""),
            Gate("Requirements", "requirements.md", "approved", "2026-07-17", "a1b2c3d"),
            Gate("Design", "design.md", "approved", "2026-07-29", "9e04f77"),
            Gate("Build", "tasks.md", "current", "", ""),
            Gate("Handoff", "README.md", "pending", "", ""),
        ),
        is_repo=True,
        feed=Feed(
            (Event("2026-08-16T10:00:00+00:00", "a1b2c3d", "task.status",
                   "T1", "T1 todo → done", "milestone"),),
            1, 0, True, 0,
        ),
        days_in_gate=None,
        days_since_commit=None,
    )
    base.update(overrides)
    return State(**base)


class TestRenderDoctrine(unittest.TestCase):
    """The rule the whole design rests on: an unknown state must never render
    as a confident zero, an empty bar, or a tick."""

    def test_absent_tasks_file_says_so_and_shows_no_percentage(self):
        html = render.body(_state(tasks=parse_tasks(None)))
        self.assertIn("produced at gate 2", html.lower())
        self.assertNotIn("0%", html)
        # `render.body` never emits a literal percentage anywhere, by
        # construction — assertNotIn("0%", ...) alone is unfailable. The bar
        # only ever appears once counts have actually been computed, so its
        # absence is the meaningful assertion here (matches the sibling
        # unreadable-header test below).
        self.assertNotIn('class="gf-bar"', html)

    def test_unreadable_header_names_the_problem_and_draws_no_counts(self):
        html = render.body(_state(tasks=parse_tasks(REORDERED_HEADER)))
        self.assertIn("header not recognised", html.lower())
        self.assertNotIn("0%", html)
        self.assertNotIn('class="gf-bar"', html)

    def test_unreadable_header_does_not_say_it_twice(self):
        # E2E-1: the Problem message from parse.py already begins with
        # "header not recognised — expected exactly: …"; render.py must not
        # prepend the same phrase a second time.
        html = render.body(_state(tasks=parse_tasks(REORDERED_HEADER)))
        self.assertEqual(html.lower().count("header not recognised"), 1)

    def test_unreadable_tasks_file_shows_no_coverage_flags_or_findings(self):
        # C2 reproduction: a reordered tasks.md header must not produce
        # confident zeros drawn from a file the parser refused to read.
        unreadable = parse_tasks(REORDERED_HEADER)
        findings = analyse.findings(
            engagement=parse_engagement(VALID_ENGAGEMENT),
            reqs=parse_requirements(VALID_REQS),
            tasks=unreadable,
            signoffs=parse_signoffs(VALID_SIGNOFFS),
            signoff_status={
                ("a1b2c3d", "requirements.md"): "unchanged",
                ("9e04f77", "design.md"): "unchanged",
            },
            status_age_days=None,
            cadence_days=7,
        )
        html = render.body(_state(tasks=unreadable, findings=findings))
        self.assertNotIn("✕ no tasks", html)
        self.assertFalse(any("unplanned work" in f.detail for f in findings))
        self.assertIn("coverage cannot be computed", html.lower())

    def test_absent_tasks_file_coverage_message_differs_from_unreadable_and_from_checked(self):
        # C2's "Absent is a defensible separate case but must still be
        # visually distinct from 'we checked and found none'" — an absent
        # tasks.md must not show the same "✕ no tasks" flag a genuinely
        # empty, valid tasks.md shows, and its message must differ from the
        # "unreadable" (present but header not ok) case too.
        absent_html = render.body(_state(tasks=parse_tasks(None)))
        unreadable_html = render.body(_state(tasks=parse_tasks(REORDERED_HEADER)))
        self.assertNotIn("✕ no tasks", absent_html)
        self.assertIn("not available yet", absent_html.lower())
        self.assertNotIn("cannot be computed", absent_html.lower())
        self.assertNotIn("not available yet", unreadable_html.lower())

    def test_dropped_tasks_are_shown_beside_the_hero_figure(self):
        # C3: dropped is excluded from the denominator and must be shown as
        # a separate count, or a scope cut silently flatters the ratio.
        tasks = _tasks(
            "| T1 | Add export | R8 | (unassigned) | done | NWT-1 |\n",
            "| T2 | Add import | R8 | (unassigned) | dropped | NWT-2 |\n",
        )
        html = render.body(_state(tasks=tasks))
        self.assertIn("gf-dropped", html)
        self.assertIn("1 dropped", html)

    def test_no_dropped_tasks_shows_no_dropped_count(self):
        tasks = _tasks("| T1 | Add export | R8 | (unassigned) | done | NWT-1 |\n")
        html = render.body(_state(tasks=tasks))
        self.assertNotIn("gf-dropped", html)
        self.assertNotIn("0 dropped", html)

    def test_valid_empty_file_reads_differently_from_an_absent_one(self):
        empty = render.body(_state(tasks=parse_tasks(EMPTY_TASKS)))
        absent = render.body(_state(tasks=parse_tasks(None)))
        self.assertNotEqual(empty, absent)

    def test_unverifiable_signoff_never_renders_a_tick(self):
        state = _state(
            signoff_status={("a1b2c3d", "requirements.md"): "unverifiable"},
            gates=(Gate("Requirements", "requirements.md", "unverifiable", "2026-07-17", "a1b2c3d"),),
        )
        html = render.body(state)
        self.assertIn("cannot verify", html.lower())
        self.assertIn("a1b2c3d", html)
        # The tick is reserved for a verified approval and must appear nowhere here.
        self.assertNotIn("✓", html)

    def test_uncovered_requirement_is_drawn_not_left_blank(self):
        html = render.body(_state())
        self.assertIn("gf-empty", html)

    def test_no_git_repo_says_no_history_rather_than_an_empty_chart(self):
        # Tasks must be non-empty, or the panel returns before reaching the trend
        # and the assertion would pass without exercising anything.
        tasks = _tasks("| T1 | Add export | R8 | (unassigned) | todo | NWT-1 |\n")
        html = render.body(_state(tasks=tasks, is_repo=False))
        self.assertIn("no git history available", html.lower())
        self.assertNotIn("<svg", html)

    def test_clean_attention_panel_is_present_and_says_nothing_right_now(self):
        html = render.body(_state(findings=()))
        self.assertIn("Needs attention", html)
        self.assertIn("Nothing right now", html)

    def test_cannot_read_history_says_so_rather_than_no_history_yet(self):
        # Deferred-4: git itself failing to be read must not be indistinguishable
        # from "read git fine, no history yet" — the former is a false positive.
        tasks = _tasks("| T1 | Add export | R8 | (unassigned) | todo | NWT-1 |\n")
        html = render.body(_state(tasks=tasks, trend=analyse.trend(False, ())))
        self.assertIn("cannot read history", html.lower())


class TestFeedLedLayout(unittest.TestCase):
    def test_feed_precedes_coverage_in_the_document(self):
        html = render.body(_state())
        self.assertLess(html.index("gf-feed"), html.index("Requirement coverage"))

    def test_gate_rail_still_shows_every_gate(self):
        html = render.body(_state())
        for name in ("Discovery", "Requirements", "Design", "Build", "Handoff"):
            self.assertIn(name, html)

    def test_days_in_gate_absent_says_nothing_rather_than_zero(self):
        html = render.body(_state(days_in_gate=None))
        self.assertNotIn("0 days in gate", html)

    def test_days_in_gate_renders_the_number_when_known(self):
        # The absent-case test above passes with both render lines deleted:
        # a page that never mentions the gate age satisfies "does not say 0".
        # This is the half that fails if the feature is missing.
        html = render.body(_state(days_in_gate=17))
        self.assertIn("17 days in gate", html)


class TestTaskFilter(unittest.TestCase):
    def _html(self):
        tasks = _tasks(
            "| T1 | Add export | R8 | (unassigned) | done | NWT-1 |\n",
            "| T2 | Add import | R8 | (unassigned) | blocked | NWT-2 |\n",
        )
        return render._tasks_panel(_state(tasks=tasks))

    def test_every_task_row_carries_its_status(self):
        html = self._html()
        self.assertIn('data-status="done"', html)
        self.assertIn('data-status="blocked"', html)

    def test_chips_exist_for_each_status_with_counts(self):
        html = self._html()
        self.assertIn('data-filter="blocked"', html)
        self.assertIn('data-filter="all"', html)

    def test_task_titles_are_present_so_filtering_needs_no_fetch(self):
        html = self._html()
        self.assertIn("Add import", html)

    def test_empty_result_message_is_in_the_dom(self):
        self.assertIn("No tasks with that status", self._html())

    def test_empty_result_message_is_hidden_by_default(self):
        # Task-8 gap #2: the prior test checked only the text, not the
        # `hidden` attribute. If this became conditionally rendered instead
        # of always-hidden-until-JS-unhides-it, FEED_JS would have nothing
        # to unhide and an empty filter would show a blank region instead of
        # this message.
        self.assertIn('class="gf-none gf-nomatch" hidden', self._html())

    def test_chip_styling_exists(self):
        # The chips carry their selected state entirely through `.gf-chip.on`.
        # Without the rule, filtering still works but the active filter is
        # invisible, which reads as a broken list rather than a filtered one.
        self.assertIn(".gf-chip.on", render.CSS)

    def test_panel_has_no_chips_when_tasks_file_is_unreadable(self):
        # Task-8 gap #1: no prior test pinned that gf-chips is absent when
        # the parser refused to read tasks.md. A regression emitting chips
        # here would offer a filter over a file that was never actually
        # parsed. Scoped to _tasks_panel (not the full body): since Task 10
        # the activity feed's own range chips share the "gf-chips" class and
        # render unconditionally, so a whole-body check on that class alone
        # would trip on those instead of the task-filter chips this test
        # actually guards. See the whole-page data-filter tests below for
        # the complementary end-to-end check.
        html = render._tasks_panel(_state(tasks=parse_tasks(REORDERED_HEADER)))
        self.assertNotIn("gf-chips", html)

    def test_panel_has_no_chips_when_tasks_file_is_absent(self):
        html = render._tasks_panel(_state(tasks=parse_tasks(None)))
        self.assertNotIn("gf-chips", html)

    def test_page_has_no_task_filter_chips_when_tasks_file_is_unreadable(self):
        # Whole-page counterpart to the panel-level test above. Rescoping
        # that test to _tasks_panel (Task 10, the gf-chips collision with
        # the feed's range toggle) left nothing checking that _tasks_panel's
        # output actually reaches body() -- a regression that dropped the
        # panel from body() entirely would still pass the panel-level test.
        # data-filter is used only by the task-status chips (_task_rows), so
        # unlike "gf-chips" it is not shared with the feed's range toggle and
        # can be asserted against the whole page without collision.
        html = render.body(_state(tasks=parse_tasks(REORDERED_HEADER)))
        self.assertNotIn("data-filter", html)

    def test_page_has_no_task_filter_chips_when_tasks_file_is_absent(self):
        html = render.body(_state(tasks=parse_tasks(None)))
        self.assertNotIn("data-filter", html)

    def test_page_has_task_filter_chips_for_a_healthy_tasks_file(self):
        # The positive counterpart the two absence tests above need: without
        # it, a mutant that never renders chips anywhere -- healthy tasks.md
        # or not -- would satisfy both absence tests while the filter UI is
        # simply gone from the page.
        tasks = _tasks(
            "| T1 | Add export | R8 | (unassigned) | done | NWT-1 |\n",
            "| T2 | Add import | R8 | (unassigned) | blocked | NWT-2 |\n",
        )
        html = render.body(_state(tasks=tasks))
        self.assertIn('data-filter="all"', html)
        self.assertIn('data-filter="blocked"', html)


class TestRenderTrend(unittest.TestCase):
    """I2a: the trend SVG (render.py's `_trend`) had zero test coverage —
    `_state()` hardcoded `trend=analyse.trend(())` and nothing overrode it,
    which is how I1 (leading/trailing gaps never drawn) survived."""

    def _revisions(self):
        readable_a = self._revision(remaining=10)
        readable_b = self._revision(remaining=4)
        return (
            ("2026-07-01T10:00:00+00:00", "garbage — leading gap"),
            ("2026-07-10T10:00:00+00:00", readable_a),
            ("2026-07-20T10:00:00+00:00", "garbage — middle gap"),
            ("2026-08-01T10:00:00+00:00", readable_b),
            ("2026-08-10T10:00:00+00:00", "garbage — trailing gap"),
        )

    @staticmethod
    def _revision(remaining: int) -> str:
        rows = "".join(
            f"| T{i} | A | R1 | (unassigned) | todo | x |\n" for i in range(remaining)
        )
        return EMPTY_TASKS + rows

    def _html(self, tasks=None):
        # The trend panel only renders once _tasks_panel gets past its own
        # "no tasks yet" early return, so the current tasks.md must be
        # non-empty here even though the trend is built from git history.
        trend = analyse.trend(True, self._revisions())
        if tasks is None:
            tasks = _tasks("| T1 | Add export | R8 | (unassigned) | todo | NWT-1 |\n")
        return render.body(_state(tasks=tasks, trend=trend, is_repo=True))

    def test_leading_middle_and_trailing_gaps_each_render_a_marker(self):
        html = self._html()
        self.assertEqual(html.count(">unreadable<"), 3)

    def test_only_the_middle_gap_gets_a_dashed_bridge(self):
        # Leading/trailing gaps have no readable point on the missing side to
        # bridge to or from, so only the one gap *between* two readable runs
        # draws a connecting dashed line.
        html = self._html()
        self.assertEqual(html.count('stroke-dasharray="3 3"'), 1)

    def test_footnote_states_totals_at_each_end(self):
        html = self._html()
        self.assertIn("10 → 4", html)

    def test_footnote_names_the_unreadable_count(self):
        html = self._html()
        self.assertIn("3 revisions could not be parsed, plotted as a gap", html)

    def test_footnote_includes_dropped_count_when_nonzero(self):
        tasks = _tasks(
            "| T1 | Add export | R8 | (unassigned) | done | NWT-1 |\n",
            "| T2 | Add import | R8 | (unassigned) | dropped | NWT-2 |\n",
        )
        html = self._html(tasks=tasks)
        self.assertIn("10 → 4, 1 dropped", html)

    def test_footnote_omits_dropped_when_zero(self):
        # C3 requires the dropped count in two places — the trend footnote and
        # beside the hero — and in neither when it is zero. Assert both
        # directly rather than scanning the whole body: unrelated copy may
        # legitimately use the word (the Remaining stat explains itself as
        # "not done, not dropped"), and a whole-body scan would fail on that
        # while proving nothing about the two places that carry the rule.
        html = self._html()
        footnote = html.split('class="gf-foot">')[1].split("</div>")[0]
        self.assertNotIn("dropped", footnote)
        self.assertNotIn('class="gf-dropped"', html)

    def test_axis_labels_use_the_readable_endpoints_not_the_gaps(self):
        html = self._html()
        self.assertIn("10 Jul", html)
        self.assertIn("1 Aug", html)

    def test_aria_label_names_the_unreadable_count(self):
        html = self._html()
        self.assertIn("3 unreadable revision(s) plotted as a gap", html)


class TestRenderBasics(unittest.TestCase):
    def test_page_is_a_full_document_with_theme_blocks(self):
        html = render.page(_state())
        self.assertTrue(html.lstrip().startswith("<!doctype html>"))
        self.assertIn("prefers-color-scheme: dark", html)
        self.assertIn('data-theme="dark"', html)

    def test_client_name_appears(self):
        self.assertIn("Northwind Trading", render.body(_state()))

    def test_html_is_escaped(self):
        # The primary escaping guarantee must be proven on content the design
        # actually renders visibly. Requirement text (gf-rtext) is
        # user-edited and always shown in the coverage table -- unlike the
        # old target (the mini-bar tooltip), which nothing else in the
        # renderer outputs, so removing that tooltip would silently drop
        # this test's coverage of the escaping bug class entirely.
        reqs = parse_requirements(
            VALID_REQS.replace(
                "| R1 | Customer can place an order | Order appears in the admin list |",
                "| R1 | <script>alert(1)</script> | Order appears in the admin list |",
            )
        )
        html = render.body(_state(reqs=reqs))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_coverage_tooltip_and_aria_label_are_escaped(self):
        tasks = _tasks("| T1 | <script>alert(2)</script> | R1 | (unassigned) | todo | x |\n")
        html = render.body(_state(tasks=tasks))
        self.assertNotIn("<script>alert(2)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_coverage_minibar_is_accessible(self):
        tasks = _tasks("| T1 | Add export | R8 | (unassigned) | done | NWT-1 |\n")
        html = render.body(_state(tasks=tasks))
        self.assertIn('role="img"', html)
        self.assertIn('aria-label="T1: Add export"', html)

    def test_poll_js_reads_html_key_not_body(self):
        # Build the same payload shape serve.py's /api/state handler emits
        # (see do_GET) and assert its key set directly, rather than only
        # checking the JS source text. Renaming the key in serve.py alone,
        # with POLL_JS left unchanged, previously still passed this test --
        # it exercised only the JS side. A live round-trip through the real
        # HTTP handler is in TestHTTPHandler below; this check pins the
        # contract both sides are supposed to agree on.
        payload_keys = {"hash", "html", "at"}
        self.assertIn("html", payload_keys)
        self.assertNotIn("body", payload_keys)
        self.assertIn("data.html", render.POLL_JS)
        self.assertNotIn("data.body", render.POLL_JS)

    def test_findings_render_with_icon_and_word_not_colour_alone(self):
        from dashboard.model import Finding

        html = render.body(_state(findings=(Finding("critical", "A problem", "Details here"),)))
        self.assertIn("A problem", html)
        self.assertIn("Details here", html)
        self.assertIn("gf-ico crit", html)


class TestCoverageExpansion(unittest.TestCase):
    def test_rows_are_details_elements(self):
        html = render._coverage(_state())
        self.assertIn("<details", html)
        self.assertIn("<summary", html)

    def test_acceptance_criterion_is_present_in_the_html(self):
        # It must be in the DOM, not fetched — the row has to work with
        # JavaScript disabled.
        html = render._coverage(_state())
        self.assertIn("Order appears in the admin list", html)

    def test_tasks_and_item_ids_appear_in_the_expansion(self):
        tasks = _tasks("| T1 | Add export | R8 | (unassigned) | done | NWT-104 |\n")
        html = render._coverage(_state(tasks=tasks))
        self.assertIn("NWT-104", html)
        self.assertIn("Add export", html)

    def test_missing_criterion_says_so_rather_than_showing_an_empty_quote(self):
        reqs = parse_requirements(
            "# Requirements\n\n## Functional\n\n"
            "| # | Requirement | Acceptance criterion |\n|---|---|---|\n"
            "| R1 | Place an order |  |\n"
        )
        html = render._coverage(_state(reqs=reqs))
        self.assertIn("no acceptance criterion", html.lower())

    def test_criterion_is_escaped(self):
        reqs = parse_requirements(
            "# Requirements\n\n## Functional\n\n"
            "| # | Requirement | Acceptance criterion |\n|---|---|---|\n"
            "| R1 | X | <script>alert(1)</script> |\n"
        )
        html = render._coverage(_state(reqs=reqs))
        self.assertNotIn("<script>alert(1)</script>", html)


from dashboard import serve  # noqa: E402

import http.client  # noqa: E402
import json as _json  # noqa: E402
import os  # noqa: E402
import threading  # noqa: E402


class TestBuildState(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.engagement_dir = self.root / "docs" / "engagement"
        self.engagement_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_engagement_dir_is_reported_not_crashed(self):
        with tempfile.TemporaryDirectory() as empty:
            state = serve.build_state(Path(empty))
            self.assertFalse(state.engagement.present)

    def test_reads_the_files_that_exist_and_marks_the_rest_absent(self):
        (self.engagement_dir / "engagement.md").write_text(VALID_ENGAGEMENT)
        state = serve.build_state(self.root)
        self.assertTrue(state.engagement.present)
        self.assertFalse(state.tasks.present)
        self.assertFalse(state.reqs.present)

    def test_non_git_directory_sets_is_repo_false(self):
        (self.engagement_dir / "engagement.md").write_text(VALID_ENGAGEMENT)
        self.assertFalse(serve.build_state(self.root).is_repo)


class TestGates(unittest.TestCase):
    def test_approved_gate_is_approved_when_unchanged(self):
        gates = serve.gates_from(parse_signoffs(VALID_SIGNOFFS), {
            ("a1b2c3d", "requirements.md"): "unchanged",
            ("9e04f77", "design.md"): "unchanged",
        })
        by_name = {g.name: g for g in gates}
        self.assertEqual(by_name["Requirements"].state, "approved")

    def test_changed_artifact_is_not_approved(self):
        gates = serve.gates_from(parse_signoffs(VALID_SIGNOFFS), {
            ("a1b2c3d", "requirements.md"): "changed",
            ("9e04f77", "design.md"): "unchanged",
        })
        by_name = {g.name: g for g in gates}
        # "changed" and "unverifiable" are different facts and must not be
        # merged. Both block approval, but the rail prints a different
        # sentence for each, and the merged version told the reader the
        # signed commit "is not in this repository" when it was sitting in
        # the log — the artifact had simply moved since.
        self.assertEqual(by_name["Requirements"].state, "changed")
        self.assertNotEqual(by_name["Requirements"].state, "approved")

    def test_gate_after_the_last_approved_one_is_current(self):
        gates = serve.gates_from(parse_signoffs(VALID_SIGNOFFS), {
            ("a1b2c3d", "requirements.md"): "unchanged",
            ("9e04f77", "design.md"): "unchanged",
        })
        by_name = {g.name: g for g in gates}
        self.assertEqual(by_name["Build"].state, "current")
        self.assertEqual(by_name["Handoff"].state, "pending")

    def test_all_five_gates_are_always_present(self):
        gates = serve.gates_from(parse_signoffs(None), {})
        self.assertEqual(len(gates), 5)

    def test_two_gates_at_the_same_commit_are_tracked_independently(self):
        # C1 regression guard: two sign-off rows sharing one commit (the
        # normal case when a gate produces several artifacts committed
        # together — see commands/gate.md) must not collapse to a single
        # commit-keyed entry. One artifact changing after sign-off must not
        # silently approve the other.
        signoffs_text = (
            "# Sign-offs\n\n"
            "| Gate | Artifact | Commit | Approved by | Date | Evidence |\n"
            "|---|---|---|---|---|---|\n"
            "| Discovery | discovery.md | 3bdbf6b | Jane Doe | 2026-07-17 | x |\n"
            "| Requirements | requirements.md | 3bdbf6b | Jane Doe | 2026-07-17 | x |\n"
        )
        status = {
            ("3bdbf6b", "discovery.md"): "unchanged",
            ("3bdbf6b", "requirements.md"): "changed",
        }
        gates = serve.gates_from(parse_signoffs(signoffs_text), status)
        by_name = {g.name: g for g in gates}
        self.assertEqual(by_name["Discovery"].state, "approved")
        self.assertEqual(by_name["Requirements"].state, "changed")


class TestDriftDiff(unittest.TestCase):
    def test_a_drift_with_no_diff_says_so_rather_than_showing_nothing(self):
        # "Nothing changed" and "the comparison could not be made" are
        # opposite claims about whether the client's approval still holds.
        html = render._drift(Drift("requirements.md", "abc1234", None, 0,
                                   "the approved version could not be read"))
        self.assertIn("Cannot show what changed", html)
        self.assertNotIn("gf-diff", html)

    def test_added_and_removed_lines_are_distinguishable(self):
        html = render._drift(Drift("requirements.md", "abc1234",
                                   ("@@ -1 +1 @@", "-old text", "+new text"), 0))
        self.assertIn("gf-dl del", html)
        self.assertIn("gf-dl add", html)
        self.assertIn("abc1234", html)

    def test_truncation_is_stated_not_silent(self):
        html = render._drift(Drift("requirements.md", "abc1234", ("+a",), 39))
        self.assertIn("39 more lines", html)

    def test_one_truncated_line_reads_singular(self):
        html = render._drift(Drift("requirements.md", "abc1234", ("+a",), 1))
        self.assertIn("1 more line;", html)

    def test_nothing_renders_when_there_is_no_drift(self):
        self.assertEqual(render._drift(None), "")


class TestGridCanShrink(unittest.TestCase):
    def test_layout_tracks_allow_their_content_to_overflow_internally(self):
        # A grid or flex item defaults to min-width:auto and will not shrink
        # below its content. One wide pre-formatted diff line therefore pushed
        # the right column out and squeezed the activity feed into a vertical
        # ribbon — twice, in two different containers. Nothing failed; it was
        # only visible in a screenshot.
        self.assertRegex(render.CSS, r"\.gf-row\s*>\s*\*\s*\{[^}]*min-width:\s*0")
        self.assertRegex(render.CSS, r"\.gf-item\s*>\s*div:last-child\s*\{[^}]*min-width:\s*0")
        # And the diff must do its own scrolling rather than widening the page.
        self.assertRegex(render.CSS, r"\.gf-diff\s*\{[^}]*overflow-x:\s*auto")


class TestCssCustomProperties(unittest.TestCase):
    def test_every_variable_used_is_defined(self):
        # An undefined custom property does not error — it falls back to the
        # inherited value and the page renders wrong quietly. Three invented
        # ones (--bg, --line, --accent) shipped in the navigation and produced
        # dark text on a dark background; nothing failed, nothing warned, and
        # it was only visible in a screenshot.
        # Only properties used WITHOUT a fallback. `var(--x, blue)` cannot
        # render wrong — CSS falls back by design — and flagging it would
        # push people away from a legitimate feature.
        used = set(re.findall(r"var\(\s*(--[a-z0-9-]+)\s*\)", render.CSS))
        defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", render.CSS))
        self.assertTrue(used, "found no custom properties — the regex has rotted")
        missing = sorted(used - defined)
        self.assertEqual(
            missing, [],
            "CSS uses custom properties that are never defined: " + ", ".join(missing),
        )


class TestFootnoteGrammar(unittest.TestCase):
    def test_a_single_commit_is_not_described_as_commits(self):
        # A brand-new engagement has exactly one commit, so this is among the
        # first sentences anyone reads from the product.
        feed = Feed((), 1, 0, True, 0)
        html = render._feed(_state(feed=feed))
        self.assertIn("1 commit scanned", html)
        self.assertNotIn("1 commits scanned", html)

    def test_several_commits_still_read_as_plural(self):
        feed = Feed((), 24, 0, True, 0)
        html = render._feed(_state(feed=feed))
        self.assertIn("24 commits scanned", html)


class TestFeedHeadingSeparation(unittest.TestCase):
    def test_card_heading_separates_its_two_children(self):
        # The feed heading holds "Activity" and a count span that FEED_JS
        # fills in. With .gf-h as a plain block the two rendered flush
        # against each other — the live page read "ACTIVITYNO PREVIOUS VISIT
        # RECORDED — SHOWING THE LAST 7 DAYS". Only visible by looking at it;
        # every assertion in this suite passed.
        self.assertRegex(render.CSS, r"\.gf-h \{[^}]*display:\s*flex")
        self.assertRegex(render.CSS, r"\.gf-h \{[^}]*justify-content:\s*space-between")


class TestTaskOwner(unittest.TestCase):
    H = ("| ID | Task | Req | Owner | Status | Item |\n"
         "|---|---|---|---|---|---|\n")

    def test_a_blank_owner_is_refused(self):
        # "nobody is on this" and "nobody filled this in" are different
        # problems on a team, so the column is never allowed to be empty.
        f = parse_tasks(self.H + "| T1 | Add thing | R1 |  | todo | X-1 |\n")
        self.assertEqual(f.tasks, ())
        self.assertIn("Owner is blank", f.problems[0].message)

    def test_unassigned_is_a_real_value(self):
        f = parse_tasks(self.H + "| T1 | Add thing | R1 | (unassigned) | todo | X-1 |\n")
        self.assertEqual(f.tasks[0].owner, "(unassigned)")
        self.assertEqual(f.problems, ())

    def test_the_owner_reaches_the_page(self):
        # It exists in the file and is invisible in the product unless it is
        # rendered — the failure mode this project has hit three times.
        tasks = _tasks("| T1 | Add thing | R1 | Priya Nair | in-progress | X-1 |\n")
        html = render.body(_state(tasks=tasks))
        # Asserted on the VISIBLE span, not just the name. The first version
        # checked for "Priya Nair" anywhere and passed with the span deleted,
        # because data-owner="Priya Nair" stays on the row for the client
        # script — an attribute a person cannot read satisfying a test about
        # whether a person can read it.
        self.assertRegex(html, r'<span class="gf-owner[^"]*">Priya Nair</span>')
        self.assertIn('data-owner="Priya Nair"', html)

    def test_unassigned_is_shown_not_hidden(self):
        # An in-progress task with nobody on it is the thing worth noticing.
        tasks = _tasks("| T1 | Add thing | R1 | (unassigned) | in-progress | X-1 |\n")
        html = render.body(_state(tasks=tasks))
        self.assertRegex(html, r'<span class="gf-owner none">\(unassigned\)</span>')


class TestDecisionLog(unittest.TestCase):
    HEADER = ("| ID | Date | Decision | Why | Instead of | Decided by |\n"
              "|---|---|---|---|---|---|\n")

    def test_a_decision_without_a_reason_is_refused(self):
        # The reason is the entire artifact. A log of what was decided and not
        # why is a list of arbitrary-looking constraints, and the next team
        # deletes them believing they were arbitrary.
        f = parse_decisions(self.HEADER
                            + "| D1 | 2026-08-20 | Reuse auth |  | Our own | R.M |\n")
        self.assertEqual(f.decisions, ())
        self.assertIn("no 'Why'", f.problems[0].message)

    def test_a_complete_decision_parses(self):
        f = parse_decisions(self.HEADER
                            + "| D1 | 2026-08-20 | Reuse auth | They run it | Our own | R.M |\n")
        self.assertEqual(len(f.decisions), 1)
        self.assertEqual(f.decisions[0].why, "They run it")
        self.assertEqual(f.decisions[0].instead_of, "Our own")
        self.assertEqual(f.problems, ())

    def test_a_reversal_is_a_new_row_and_both_survive(self):
        # Append-only. Editing the original destroys the record that a choice
        # was made, on a date, for a reason that seemed good at the time.
        f = parse_decisions(self.HEADER
            + "| D1 | 2026-08-01 | Poll the ERP | No webhook available | A webhook | Team |\n"
            + "| D3 | 2026-08-06 | Use the file drop | IT surfaced an export | Polling, per D1 | Team |\n")
        self.assertEqual([d.id for d in f.decisions], ["D1", "D3"])

    def test_the_header_is_load_bearing(self):
        f = parse_decisions("| ID | Date | Decision | Reason | Instead of | Decided by |\n"
                            "|---|---|---|---|---|---|\n")
        self.assertFalse(f.header_ok)
        self.assertIn("header not recognised", f.problems[0].message)


class TestReApprovalSupersedes(unittest.TestCase):
    """Re-approving a gate is the methodology's remedy for drift. Both halves
    of the product must agree that it worked."""

    TWO = (
        "# Sign-offs\n\n"
        "| Gate | Artifact | Commit | Approved by | Date | Evidence |\n"
        "|---|---|---|---|---|---|\n"
        "| Design | design.md | aaaaaaa | A Client | 2026-08-20 | e1 |\n"
        "| Design | design.md | bbbbbbb | A Client | 2026-08-21 | e2 — re-approved |\n"
    )

    def test_only_the_latest_row_counts(self):
        parsed = parse_signoffs(self.TWO)
        live = analyse.current_signoffs(parsed)
        self.assertEqual([s.commit for s in live], ["bbbbbbb"])

    def test_a_superseded_row_is_not_a_live_finding(self):
        # The defect: the old approval stayed CRITICAL for the rest of the
        # engagement while the gate rail showed the gate approved — the
        # product contradicting itself about one gate at one moment.
        parsed = parse_signoffs(self.TWO)
        found = analyse.findings(
            parse_engagement(VALID_ENGAGEMENT), parse_requirements(VALID_REQS),
            _tasks(), parsed,
            {("aaaaaaa", "design.md"): "changed",
             ("bbbbbbb", "design.md"): "unchanged"},
            None, 7,
        )
        self.assertFalse(
            [f for f in found if "design.md changed after sign-off" == f.label],
            "a superseded approval must not stay a live finding",
        )

    def test_drift_on_the_CURRENT_approval_still_fires(self):
        # The other half: superseding must not become a way to silence drift.
        parsed = parse_signoffs(self.TWO)
        found = analyse.findings(
            parse_engagement(VALID_ENGAGEMENT), parse_requirements(VALID_REQS),
            _tasks(), parsed,
            {("aaaaaaa", "design.md"): "unchanged",
             ("bbbbbbb", "design.md"): "changed"},
            None, 7,
        )
        self.assertTrue(
            [f for f in found if "design.md changed after sign-off" == f.label],
            "drift against the current approval must still be reported",
        )


class TestChangedGateWording(unittest.TestCase):
    def test_changed_gate_does_not_claim_the_commit_is_missing(self):
        # The defect this pins: a gate whose artifact changed after sign-off
        # rendered "cannot verify: commit <sha> is not in this repository".
        # The commit was in the repository. A reader would go looking for a
        # commit that was never lost, and would not learn that the approved
        # artifact had drifted — which is the finding the whole gate exists
        # to surface.
        html = render.body(_state(gates=(
            Gate("Discovery", "discovery.md", "approved", "2026-07-13", "b367d72"),
            Gate("Requirements", "requirements.md", "changed", "2026-07-15", "20d68a5"),
        )))
        self.assertNotIn("is not in this repository", html)
        self.assertIn("changed since 20d68a5", html)

    def test_headline_surfaces_a_changed_gate_not_just_a_missing_one(self):
        # Regression: when "changed" was split out of "unverifiable", _phase
        # still looked only for "unverifiable", so the top line read "Build in
        # progress" on an engagement whose Requirements sign-off had drifted.
        # The rail said so; the headline did not.
        html = render.body(_state(gates=(
            Gate("Requirements", "requirements.md", "changed", "2026-07-15", "20d68a5"),
            Gate("Build", "tasks.md", "current", "", ""),
        )))
        self.assertIn("Requirements sign-off needs re-checking", html)
        self.assertNotIn("Build in progress", html)

    def test_genuinely_missing_commit_still_says_so(self):
        # The other half: separating the states must not silence the real
        # "cannot verify" case.
        html = render.body(_state(gates=(
            Gate("Requirements", "requirements.md", "unverifiable", "2026-07-15", "deadbee"),
        )))
        self.assertIn("is not in this repository", html)


class TestCachedState(unittest.TestCase):
    """Gap 1 of t11-supplement.md: build_state performs ~45 subprocess spawns
    on a six-week engagement; the browser polls /api/state every 2 seconds
    forever. cached_state must avoid recomputation when nothing changed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "t@example.com")
        _git(self.root, "config", "user.name", "Test")
        self.engagement_dir = self.root / "docs" / "engagement"
        self.engagement_dir.mkdir(parents=True)
        (self.engagement_dir / "engagement.md").write_text(VALID_ENGAGEMENT)
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "first")
        serve._cache["key"] = None
        serve._cache["state"] = None

    def tearDown(self):
        serve._cache["key"] = None
        serve._cache["state"] = None
        self._tmp.cleanup()

    def test_repeat_calls_with_no_change_return_the_same_object(self):
        first = serve.cached_state(self.root)
        second = serve.cached_state(self.root)
        self.assertIs(first, second)

    def test_touching_tasks_md_invalidates_the_cache(self):
        first = serve.cached_state(self.root)
        tasks_path = self.engagement_dir / "tasks.md"
        tasks_path.write_text(VALID_TASKS)
        bumped = (tasks_path.stat().st_mtime or 0) + 5
        os.utime(tasks_path, (bumped, bumped))
        second = serve.cached_state(self.root)
        self.assertIsNot(first, second)

    def test_build_state_itself_remains_uncached(self):
        first = serve.build_state(self.root)
        second = serve.build_state(self.root)
        self.assertIsNot(first, second)

    def test_cache_actually_prevents_repeat_git_work(self):
        # Not just "returns the same object" — prove build_state (the thing
        # that does the ~45 subprocess spawns) is not re-invoked on a hit.
        calls = {"n": 0}
        real_build_state = serve.build_state

        def counting_build_state(root):
            calls["n"] += 1
            return real_build_state(root)

        with unittest.mock.patch.object(serve, "build_state", side_effect=counting_build_state):
            serve.cached_state(self.root)
            serve.cached_state(self.root)
            serve.cached_state(self.root)
            self.assertEqual(calls["n"], 1)

            tasks_path = self.engagement_dir / "tasks.md"
            tasks_path.write_text(VALID_TASKS)
            bumped = (tasks_path.stat().st_mtime or 0) + 5
            os.utime(tasks_path, (bumped, bumped))
            serve.cached_state(self.root)
            self.assertEqual(calls["n"], 2)


class TestArtifactPathResolution(unittest.TestCase):
    """Gap 2 of t11-supplement.md / Fix 2 of CRITICAL-false-green-tick.md: the
    Artifact column may name a file under docs/engagement/ or, for the
    Handoff gate, the repository-root README.md."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "t@example.com")
        _git(self.root, "config", "user.name", "Test")
        self.engagement_dir = self.root / "docs" / "engagement"
        self.engagement_dir.mkdir(parents=True)
        (self.engagement_dir / "requirements.md").write_text("reqs v1\n")
        (self.root / "README.md").write_text("readme v1\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "first")
        self.commit = _git(self.root, "rev-parse", "HEAD")

    def tearDown(self):
        self._tmp.cleanup()

    def test_engagement_relative_artifact_verifies_normally(self):
        status = serve._resolve_artifact_status(self.root, self.commit, "requirements.md")
        self.assertEqual(status, "unchanged")

    def test_repo_root_artifact_verifies_normally_not_a_false_alarm(self):
        status = serve._resolve_artifact_status(self.root, self.commit, "README.md")
        self.assertEqual(status, "unchanged")

    def test_artifact_in_neither_location_is_unverifiable(self):
        status = serve._resolve_artifact_status(self.root, self.commit, "nowhere.md")
        self.assertEqual(status, "unverifiable")

    def test_build_state_resolves_handoff_signoff_against_repo_root(self):
        (self.engagement_dir / "engagement.md").write_text(VALID_ENGAGEMENT)
        (self.engagement_dir / "signoffs.md").write_text(
            "# Sign-offs\n\n"
            "| Gate | Artifact | Commit | Approved by | Date | Evidence |\n"
            "|---|---|---|---|---|---|\n"
            f"| Handoff | README.md | {self.commit} | Jane Doe | 2026-08-01 | x |\n"
        )
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "second")
        state = serve.build_state(self.root)
        by_name = {g.name: g for g in state.gates}
        self.assertEqual(by_name["Handoff"].state, "approved")


class TestSameCommitTwoArtifacts(unittest.TestCase):
    """C1 end-to-end reproduction, through `serve.build_state` against a real
    git repo — not just the pure-function unit tests above. `discovery.md`
    and `requirements.md` are committed together (the normal shape for a
    gate that produces several artifacts, per commands/gate.md), both
    sign-offs are recorded at that one commit, and then `requirements.md` is
    edited and re-committed. Before the C1 fix, keying signoff_status by
    commit alone let the second row's lookup collide with the first and the
    Requirements gate rendered approved with no finding at all."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "t@example.com")
        _git(self.root, "config", "user.name", "Test")
        self.engagement_dir = self.root / "docs" / "engagement"
        self.engagement_dir.mkdir(parents=True)
        (self.engagement_dir / "engagement.md").write_text(VALID_ENGAGEMENT)
        (self.engagement_dir / "discovery.md").write_text("discovery v1\n")
        (self.engagement_dir / "requirements.md").write_text("reqs v1\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "gate 1+2 artifacts")
        self.shared_commit = _git(self.root, "rev-parse", "HEAD")

        (self.engagement_dir / "requirements.md").write_text("reqs v2 — edited after sign-off\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "edit requirements after approval")

        (self.engagement_dir / "signoffs.md").write_text(
            "# Sign-offs\n\n"
            "| Gate | Artifact | Commit | Approved by | Date | Evidence |\n"
            "|---|---|---|---|---|---|\n"
            f"| Discovery | discovery.md | {self.shared_commit} | Jane Doe | 2026-07-17 | x |\n"
            f"| Requirements | requirements.md | {self.shared_commit} | Jane Doe | 2026-07-17 | x |\n"
        )
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "record sign-offs")

    def tearDown(self):
        self._tmp.cleanup()

    def test_changed_artifact_is_not_approved_and_produces_a_finding(self):
        state = serve.build_state(self.root)
        by_name = {g.name: g for g in state.gates}
        # The artifact that did not change stays approved...
        self.assertEqual(by_name["Discovery"].state, "approved")
        # ...but the one that changed after sign-off must not collapse into
        # the same commit-keyed entry as Discovery's "unchanged" status, and
        # must report as "changed" rather than "unverifiable" — the commit is
        # present; only the artifact moved.
        self.assertEqual(by_name["Requirements"].state, "changed")
        matching = [f for f in state.findings if f.label == "requirements.md changed after sign-off"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].severity, "critical")
        self.assertFalse(
            any(f.label == "discovery.md changed after sign-off" for f in state.findings)
        )


class TestHTTPHandler(unittest.TestCase):
    """I2b: `_handler`/`serve` had zero test coverage. The loopback-only bind
    and the GET-only rule are the only security-relevant invariants in this
    feature — this page carries client name, requirements, and commercial
    state — and nothing stopped a future edit from adding a `do_POST`."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        engagement_dir = self.root / "docs" / "engagement"
        engagement_dir.mkdir(parents=True)
        (engagement_dir / "engagement.md").write_text(VALID_ENGAGEMENT)
        # Port 0: let the OS assign an ephemeral free port, so this test is
        # deterministic and does not collide with a real dashboard instance
        # or with other test runs.
        self.server = serve.ThreadingHTTPServer(
            ("127.0.0.1", 0), serve._handler(serve.slugs([self.root]))
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self._tmp.cleanup()

    def _request(self, method, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path)
            response = conn.getresponse()
            body = response.read()
            return response.status, body
        finally:
            conn.close()

    def test_binds_loopback_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_get_index_serves_html(self):
        status, body = self._request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!doctype html>", body)

    def test_get_api_state_serves_json_with_the_keys_poll_js_reads(self):
        status, body = self._request("GET", "/api/state")
        self.assertEqual(status, 200)
        payload = _json.loads(body)
        self.assertIn("hash", payload)
        self.assertIn("html", payload)
        self.assertNotIn("body", payload)

    def test_unknown_path_is_404(self):
        status, _ = self._request("GET", "/nope")
        self.assertEqual(status, 404)

    def test_post_is_rejected_with_405(self):
        status, body = self._request("POST", "/api/state")
        self.assertEqual(status, 405)
        self.assertIn(b"read-only", body)

    def test_put_is_rejected_with_405(self):
        status, _ = self._request("PUT", "/api/state")
        self.assertEqual(status, 405)

    def test_delete_is_rejected_with_405(self):
        status, _ = self._request("DELETE", "/api/state")
        self.assertEqual(status, 405)

    def test_patch_is_rejected_with_405(self):
        status, _ = self._request("PATCH", "/api/state")
        self.assertEqual(status, 405)


if __name__ == "__main__":
    unittest.main()


class TestSlugs(unittest.TestCase):
    def test_slug_comes_from_the_directory_name(self):
        pairs = serve.slugs([Path("/clients/northwind"), Path("/clients/meridian")])
        self.assertEqual([s for s, _ in pairs], ["northwind", "meridian"])

    def test_order_is_preserved(self):
        roots = [Path("/c/zeta"), Path("/c/alpha")]
        self.assertEqual([p for _, p in serve.slugs(roots)], roots)

    def test_colliding_directory_names_get_a_suffix(self):
        pairs = serve.slugs([Path("/a/acme"), Path("/b/acme"), Path("/c/acme")])
        self.assertEqual([s for s, _ in pairs], ["acme", "acme-2", "acme-3"])

    def test_slug_is_url_safe(self):
        pairs = serve.slugs([Path("/x/Big Client Ltd.")])
        self.assertEqual(pairs[0][0], "big-client-ltd")

    def test_unusable_name_falls_back_to_a_positional_slug(self):
        pairs = serve.slugs([Path("/x/...")])
        self.assertEqual(pairs[0][0], "engagement-1")


class TestIndexRender(unittest.TestCase):
    def _entries(self, *states):
        return tuple((f"e{i}", s) for i, s in enumerate(states, 1))

    def test_one_row_per_engagement(self):
        html = render.index_body(self._entries(_state(), _state()))
        self.assertEqual(html.count('class="gf-erow"'), 2)

    def test_client_name_and_link_appear(self):
        html = render.index_body((("meridian", _state()),))
        self.assertIn("Northwind Trading", html)
        self.assertIn('href="/e/meridian"', html)

    def test_path_that_is_not_an_engagement_says_so_rather_than_blank(self):
        state = _state(engagement=parse_engagement(None))
        html = render.index_body((("scratch", state),))
        self.assertIn("not an engagement", html.lower())
        # It must still be listed — silently dropping it would let the reader
        # believe they were seeing their whole portfolio.
        self.assertEqual(html.count('class="gf-erow"'), 1)

    def test_counts_degrade_rather_than_showing_zero(self):
        state = _state(tasks=parse_tasks(REORDERED_HEADER))
        html = render.index_body((("x", state),))
        self.assertIn("—", html)
        self.assertNotIn("0 / 0", html)

    def test_index_page_is_a_full_document(self):
        page = render.index_page((("x", _state()),))
        self.assertTrue(page.lstrip().startswith("<!doctype html>"))
        self.assertIn("data-set-theme", page)


class TestPortfolioRouting(unittest.TestCase):
    """Two real engagements behind one server."""

    def setUp(self):
        self._tmps = [tempfile.TemporaryDirectory() for _ in range(2)]
        self.roots = []
        for tmp, client in zip(self._tmps, ("Alpha Bank", "Beta Retail")):
            root = Path(tmp.name) / client.split()[0].lower()
            (root / "docs" / "engagement").mkdir(parents=True)
            (root / "docs" / "engagement" / "engagement.md").write_text(
                VALID_ENGAGEMENT.replace("Northwind Trading", client)
            )
            self.roots.append(root)
        self.entries = serve.slugs(self.roots)
        self.server = serve.ThreadingHTTPServer(
            ("127.0.0.1", 0), serve._handler(self.entries)
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        for tmp in self._tmps:
            tmp.cleanup()

    def _get(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def test_root_serves_the_portfolio_index_not_one_engagement(self):
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"2 engagements", body)
        self.assertIn(b"Alpha Bank", body)
        self.assertIn(b"Beta Retail", body)

    def test_each_engagement_is_reachable_by_slug(self):
        for slug, _ in self.entries:
            status, body = self._get(f"/e/{slug}")
            self.assertEqual(status, 200)
            self.assertIn(b"<!doctype html>", body)

    def test_slugs_address_different_engagements(self):
        first = self._get(f"/e/{self.entries[0][0]}")[1]
        second = self._get(f"/e/{self.entries[1][0]}")[1]
        self.assertIn(b"Alpha Bank", first)
        self.assertIn(b"Beta Retail", second)
        self.assertNotEqual(first, second)

    def test_unknown_slug_is_404_and_never_falls_back(self):
        # Falling back to some other engagement would show the reader the
        # wrong client's commercial state — the worst outcome available here.
        status, body = self._get("/e/nope")
        self.assertEqual(status, 404)
        self.assertNotIn(b"Alpha Bank", body)
        self.assertNotIn(b"Beta Retail", body)

    def test_api_state_requires_a_slug_when_several_engagements(self):
        self.assertEqual(self._get("/api/state")[0], 404)

    def test_api_state_returns_the_named_engagement(self):
        slug = self.entries[1][0]
        status, body = self._get(f"/api/state?e={slug}")
        self.assertEqual(status, 200)
        self.assertIn("Beta Retail", _json.loads(body)["html"])

    def test_write_verbs_still_rejected(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("POST", "/")
            self.assertEqual(conn.getresponse().status, 405)
        finally:
            conn.close()


class TestPerRootCache(unittest.TestCase):
    def test_two_roots_do_not_evict_each_other(self):
        serve._cache.clear()
        tmps = [tempfile.TemporaryDirectory() for _ in range(2)]
        try:
            roots = []
            for tmp in tmps:
                root = Path(tmp.name)
                (root / "docs" / "engagement").mkdir(parents=True)
                (root / "docs" / "engagement" / "engagement.md").write_text(VALID_ENGAGEMENT)
                roots.append(root)
            first_a = serve.cached_state(roots[0])
            first_b = serve.cached_state(roots[1])
            # Asking for A again must return A's cached object, not rebuild it
            # because B displaced it.
            self.assertIs(serve.cached_state(roots[0]), first_a)
            self.assertIs(serve.cached_state(roots[1]), first_b)
            self.assertEqual(len(serve._cache), 2)
        finally:
            for tmp in tmps:
                tmp.cleanup()


from dashboard import events  # noqa: E402

TASKS_HEADER_ONLY = (
    "# Tasks\n\n| ID | Task | Req | Owner | Status | Item |\n|---|---|---|---|---|---|\n"
)


def _tf(*rows):
    return parse_tasks(TASKS_HEADER_ONLY + "".join(rows))


class TestTaskEvents(unittest.TestCase):
    def test_new_task_is_added(self):
        after = _tf("| T1 | Add export | R1 | (unassigned) | todo | (pending) |\n")
        found = events.from_tasks(_tf(), after, "2026-08-16T10:00:00+00:00", "abc1234")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].kind, "task.added")
        self.assertEqual(found[0].subject, "T1")
        self.assertEqual(found[0].tone, "progress")

    def test_status_change_names_both_ends(self):
        before = _tf("| T1 | Add export | R1 | (unassigned) | todo | NWT-1 |\n")
        after = _tf("| T1 | Add export | R1 | (unassigned) | done | NWT-1 |\n")
        found = events.from_tasks(before, after, "2026-08-16T10:00:00+00:00", "abc1234")
        self.assertEqual(found[0].kind, "task.status")
        self.assertIn("todo", found[0].text)
        self.assertIn("done", found[0].text)

    def test_dropped_is_its_own_kind_with_scope_tone(self):
        before = _tf("| T1 | Add export | R1 | (unassigned) | todo | NWT-1 |\n")
        after = _tf("| T1 | Add export | R1 | (unassigned) | dropped | NWT-1 |\n")
        found = events.from_tasks(before, after, "2026-08-16T10:00:00+00:00", "abc1234")
        self.assertEqual(found[0].kind, "task.dropped")
        self.assertEqual(found[0].tone, "scope")

    def test_item_assigned_when_pending_becomes_real(self):
        before = _tf("| T1 | Add export | R1 | (unassigned) | todo | (pending) |\n")
        after = _tf("| T1 | Add export | R1 | (unassigned) | todo | NWT-104 |\n")
        found = events.from_tasks(before, after, "2026-08-16T10:00:00+00:00", "abc1234")
        self.assertEqual(found[0].kind, "task.item")
        self.assertIn("NWT-104", found[0].text)

    def test_no_change_yields_no_events(self):
        same = _tf("| T1 | Add export | R1 | (unassigned) | todo | NWT-1 |\n")
        self.assertEqual(events.from_tasks(same, same, "x", "y"), ())

    def test_first_revision_reports_added_not_a_diff(self):
        after = _tf("| T1 | A | R1 | (unassigned) | todo | x |\n", "| T2 | B | R1 | (unassigned) | todo | y |\n")
        found = events.from_tasks(None, after, "x", "y")
        self.assertEqual({e.kind for e in found}, {"task.added"})
        self.assertEqual(len(found), 2)

    def test_unreadable_revision_yields_nothing_and_does_not_raise(self):
        bad = parse_tasks("garbage with no table")
        self.assertEqual(events.from_tasks(_tf(), bad, "x", "y"), ())


REQS_ONE = """# Requirements

## Functional

| # | Requirement | Acceptance criterion |
|---|---|---|
| R1 | Place an order | Order appears in the admin list |
"""

REQS_ONE_CHANGED = REQS_ONE.replace(
    "Order appears in the admin list", "Order appears within 5 seconds"
)
REQS_TWO = REQS_ONE + "| R2 | Cancel an order | Cancelled within 1 minute |\n"


class TestDroppedTaskReturning(unittest.TestCase):
    def test_dropped_back_to_todo_reports_the_return(self):
        # Pinning current behaviour, which was never specified. A task
        # leaving scope is `task.dropped`/scope; the same task returning
        # comes back as an ordinary `task.status`/progress event. The
        # asymmetry is deliberate to leave alone here, not an oversight
        # nobody noticed: re-scoping is a scope change and arguably earns
        # the scope tone, but the tone budget is spec-fixed and widening it
        # belongs to a spec revision, not a fix wave. Recorded so the next
        # reader can tell intent from accident.
        before = parse_tasks(TASKS_HEADER_ONLY + "| T1 | A | R1 | (unassigned) | dropped | x |\n")
        after = parse_tasks(TASKS_HEADER_ONLY + "| T1 | A | R1 | (unassigned) | todo | x |\n")
        found = events.from_tasks(before, after, "w", "c")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].kind, "task.status")
        self.assertEqual(found[0].tone, "progress")
        self.assertIn("dropped", found[0].text)
        self.assertIn("todo", found[0].text)


class TestRequirementEvents(unittest.TestCase):
    def test_new_requirement_is_added(self):
        found = events.from_requirements(
            parse_requirements(REQS_ONE), parse_requirements(REQS_TWO),
            "x", "y", frozenset()
        )
        self.assertEqual(found[0].kind, "req.added")
        self.assertEqual(found[0].subject, "R2")

    def test_criterion_change_before_signoff_is_not_scope_drift(self):
        found = events.from_requirements(
            parse_requirements(REQS_ONE), parse_requirements(REQS_ONE_CHANGED),
            "x", "y", frozenset()
        )
        self.assertEqual(found[0].kind, "req.criterion")
        self.assertNotEqual(found[0].tone, "scope")

    def test_criterion_change_after_signoff_is_scope_drift(self):
        found = events.from_requirements(
            parse_requirements(REQS_ONE), parse_requirements(REQS_ONE_CHANGED),
            "x", "y", frozenset({"requirements.md"})
        )
        self.assertEqual(found[0].kind, "req.criterion")
        self.assertEqual(found[0].tone, "scope")
        self.assertIn("after", found[0].text.lower())

    def test_removed_requirement_is_reported(self):
        found = events.from_requirements(
            parse_requirements(REQS_TWO), parse_requirements(REQS_ONE),
            "x", "y", frozenset()
        )
        self.assertEqual(found[0].kind, "req.removed")
        self.assertEqual(found[0].subject, "R2")

    def test_absent_previous_yields_added_for_each(self):
        found = events.from_requirements(None, parse_requirements(REQS_TWO), "x", "y", frozenset())
        self.assertEqual({e.kind for e in found}, {"req.added"})

    def test_unparseable_version_yields_nothing(self):
        self.assertEqual(
            events.from_requirements(
                parse_requirements(REQS_ONE), parse_requirements("nothing"), "x", "y", frozenset()
            ),
            (),
        )


SIGNOFF_HEADER = (
    "# Sign-offs\n\n"
    "| Gate | Artifact | Commit | Approved by | Date | Evidence |\n"
    "|---|---|---|---|---|---|\n"
)
SIGNOFF_ONE = SIGNOFF_HEADER + (
    "| Requirements | requirements.md | a1b2c3d | Jane Doe, CTO | 2026-07-17 | https://slack/1 |\n"
)


class TestSignoffAndEngagementEvents(unittest.TestCase):
    def test_new_signoff_is_a_milestone_naming_the_approver(self):
        found = events.from_signoffs(
            parse_signoffs(SIGNOFF_HEADER), parse_signoffs(SIGNOFF_ONE), "x", "y"
        )
        self.assertEqual(found[0].kind, "gate.signed")
        self.assertEqual(found[0].subject, "Requirements")
        self.assertEqual(found[0].tone, "milestone")
        self.assertIn("Jane Doe", found[0].text)

    def test_signoff_event_carries_the_approved_commit(self):
        found = events.from_signoffs(
            parse_signoffs(SIGNOFF_HEADER), parse_signoffs(SIGNOFF_ONE), "x", "y"
        )
        self.assertIn("a1b2c3d", found[0].text)

    def test_no_new_signoff_yields_nothing(self):
        same = parse_signoffs(SIGNOFF_ONE)
        self.assertEqual(events.from_signoffs(same, same, "x", "y"), ())

    def test_epic_assigned_when_pending_becomes_real(self):
        before = parse_engagement(VALID_ENGAGEMENT)
        after = parse_engagement(VALID_ENGAGEMENT.replace("epic: NWT-142", "epic: NWT-999"))
        pending = parse_engagement(VALID_ENGAGEMENT.replace("epic: NWT-142", "epic: (pending)"))
        found = events.from_engagement(pending, after, "x", "y")
        self.assertEqual(found[0].kind, "epic.assigned")
        self.assertIn("NWT-999", found[0].text)
        del before

    def test_epic_corrected_to_a_different_real_key_is_reported(self):
        # I6. Only (pending) -> real used to fire. A real -> different-real
        # correction means every work item raised before it sits under the
        # old epic, and the feed said nothing at all.
        before = parse_engagement(VALID_ENGAGEMENT)
        after = parse_engagement(VALID_ENGAGEMENT.replace("epic: NWT-142", "epic: NWT-880"))
        found = events.from_engagement(before, after, "x", "y")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].kind, "epic.assigned")
        self.assertEqual(found[0].tone, "attention")
        self.assertIn("NWT-142", found[0].text)
        self.assertIn("NWT-880", found[0].text)

    def test_epic_event_survives_an_unrelated_problem_in_the_file(self):
        # F1. The whole-file `readable()` predicate meant any problem anywhere
        # in engagement.md suppressed the epic event. A title missing its
        # "Engagement:" prefix has nothing to do with the tracker key, but it
        # made epic.assigned disappear while the footnote's unreadable count
        # went up — the reader told something was wrong, but not that the
        # tracker key they file work under had just been set.
        broken = VALID_ENGAGEMENT.replace("# Engagement:", "#")
        before = parse_engagement(broken.replace("epic: NWT-142", "epic: (pending)"))
        after = parse_engagement(broken)
        self.assertTrue(before.problems, "fixture must actually be problematic")
        self.assertTrue(after.problems)
        found = events.from_engagement(before, after, "x", "y")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].kind, "epic.assigned")
        self.assertIn("NWT-142", found[0].text)

    def test_epic_absent_still_yields_nothing(self):
        # The other half: relaxing the predicate must not start emitting
        # events for a file whose Tracker block is gone. epic lands on "" and
        # the falsy guard rejects it.
        before = parse_engagement(VALID_ENGAGEMENT.replace("epic: NWT-142", "epic: (pending)"))
        after = parse_engagement(VALID_ENGAGEMENT.replace("epic: NWT-142", "narrative: x"))
        self.assertEqual(events.from_engagement(before, after, "x", "y"), ())

    def test_epic_unchanged_yields_nothing(self):
        same = parse_engagement(VALID_ENGAGEMENT)
        self.assertEqual(events.from_engagement(same, same, "x", "y"), ())


class TestFeedAssembly(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "t@example.com")
        _git(self.root, "config", "user.name", "Test")
        (self.root / "docs" / "engagement").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _commit(self, name, text, message):
        (self.root / "docs" / "engagement" / name).write_text(text)
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", message)

    def test_task_completion_appears_in_the_feed(self):
        self._commit("tasks.md", TASKS_HEADER_ONLY + "| T1 | A | R1 | (unassigned) | todo | x |\n", "add")
        self._commit("tasks.md", TASKS_HEADER_ONLY + "| T1 | A | R1 | (unassigned) | done | x |\n", "done")
        feed = serve.build_feed(self.root)
        self.assertTrue(feed.history_ok)
        kinds = [e.kind for e in feed.events]
        self.assertIn("task.status", kinds)

    def _commit_on(self, name, text, message, date):
        """Commit with a controlled author/committer date, so walk order and
        chronological order can be made to disagree."""
        (self.root / "docs" / "engagement" / name).write_text(text)
        env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", message], cwd=self.root,
                       check=True, capture_output=True, env=env)

    def test_newest_first(self):
        # Written with two back-to-back commits, this test could not fail:
        # `%cI` is second-resolution, both commits landed inside the same
        # second, and `>=` on equal strings passes with the sort deleted.
        # build_feed walks oldest-first so it can diff each commit against
        # its predecessor, which means events are COLLECTED oldest-first and
        # the sort is the only thing that reverses them. Distinct, ascending
        # commit dates are therefore what makes the sort load-bearing here —
        # dating them the other way round pre-sorts the list by accident and
        # the test passes with the sort deleted.
        self._commit_on("tasks.md", TASKS_HEADER_ONLY + "| T1 | A | R1 | (unassigned) | todo | x |\n",
                        "add", "2026-01-05T12:00:00+00:00")
        self._commit_on("tasks.md", TASKS_HEADER_ONLY + "| T1 | A | R1 | (unassigned) | done | x |\n",
                        "done", "2026-01-10T12:00:00+00:00")
        feed = serve.build_feed(self.root)
        whens = [e.when for e in feed.events]
        self.assertGreater(len(set(whens)), 1, "dates must differ or nothing is proved")
        self.assertEqual(whens, sorted(whens, reverse=True))

    def test_unreadable_revision_is_counted_not_dropped_silently(self):
        self._commit("tasks.md", TASKS_HEADER_ONLY + "| T1 | A | R1 | (unassigned) | todo | x |\n", "add")
        self._commit("tasks.md", "garbage with no table\n", "break")
        feed = serve.build_feed(self.root)
        self.assertGreaterEqual(feed.unreadable, 1)

    def test_one_malformed_task_row_is_counted_and_fabricates_no_added_event(self):
        # C3. A single status typo used to be invisible: the header parsed, so
        # the file read as fully understood, the typo'd row silently vanished
        # from that commit, and its return one commit later surfaced as a
        # SECOND `task.added` for a task that had existed the whole time — all
        # under a footnote asserting 0 unreadable.
        self._commit(
            "tasks.md",
            TASKS_HEADER_ONLY
            + "| T1 | A | R1 | (unassigned) | todo | x |\n| T2 | B | R1 | (unassigned) | todo | x |\n",
            "both tasks",
        )
        self._commit(
            "tasks.md",
            TASKS_HEADER_ONLY
            + "| T1 | A | R1 | (unassigned) | todo | x |\n| T2 | B | R1 | in progress | x |\n",
            "status typo: 'in progress' for 'in-progress'",
        )
        self._commit(
            "tasks.md",
            TASKS_HEADER_ONLY
            + "| T1 | A | R1 | (unassigned) | todo | x |\n| T2 | B | R1 | (unassigned) | in-progress | x |\n",
            "typo corrected",
        )
        feed = serve.build_feed(self.root)

        self.assertGreaterEqual(feed.unreadable, 1)
        added = [e for e in feed.events if e.kind == "task.added" and e.subject == "T2"]
        self.assertEqual(len(added), 1, "T2 was added once and must be reported once")
        # The real transition still surfaces: the malformed version is skipped
        # as a baseline, so the corrected commit diffs against the last good one.
        statuses = [e for e in feed.events if e.kind == "task.status"]
        self.assertEqual([e.text for e in statuses], ["T2 todo → in-progress — B"])

    def test_one_malformed_requirement_row_produces_no_removal_event(self):
        # C3, the expensive half. A four-cell row rendered as `req.removed` —
        # a scope-reduction claim manufactured from a typo, and the kind of
        # thing someone takes into a change-order conversation.
        self._commit("requirements.md", REQS_TWO, "two requirements")
        malformed = REQS_TWO.replace(
            "| R2 | Cancel an order | Cancelled within 1 minute |",
            "| R2 | Cancel an order | Cancelled within 1 minute | oops |",
        )
        self.assertNotEqual(malformed, REQS_TWO)
        self._commit("requirements.md", malformed, "widen one row by a cell")
        feed = serve.build_feed(self.root)

        self.assertGreaterEqual(feed.unreadable, 1)
        self.assertEqual([e for e in feed.events if e.kind == "req.removed"], [])

    def test_deleting_a_watched_file_is_never_a_quiet_period(self):
        # C4. `git rm docs/engagement/tasks.md` used to contribute nothing, and
        # the restoring commit bailed on `not previous.present`, so two commits
        # of real activity — including deletion of the task list — read as a
        # quiet week under a footnote asserting 0 unreadable.
        self._commit(
            "tasks.md",
            TASKS_HEADER_ONLY
            + "| T1 | A | R1 | (unassigned) | todo | x |\n| T2 | B | R1 | (unassigned) | todo | x |\n",
            "two tasks",
        )
        _git(self.root, "rm", "-q", "docs/engagement/tasks.md")
        _git(self.root, "commit", "-q", "-m", "delete the task list")
        # `git rm` takes the now-empty directory with it.
        (self.root / "docs" / "engagement").mkdir(parents=True, exist_ok=True)
        self._commit(
            "tasks.md",
            TASKS_HEADER_ONLY + "| T1 | A | R1 | (unassigned) | done | x |\n",
            "restore without T2, T1 done",
        )
        feed = serve.build_feed(self.root)

        # Either a deletion event or a non-zero unreadable count — silence in
        # both at once is the failure.
        deletions = [e for e in feed.events if "delet" in e.text.lower()]
        self.assertTrue(
            deletions or feed.unreadable,
            "a deleted watched file must be visible somewhere",
        )
        # And the restore no longer swallows what changed while the file was
        # away: T1 reaching done is real news that used to disappear entirely.
        self.assertIn(
            "task.status", [e.kind for e in feed.events],
            "the restoring commit must still be diffed against the last good version",
        )

    def test_a_commit_with_events_and_a_dropped_row_is_still_counted_unreadable(self):
        # The guard used to be `if not produced and _unparsed(...)`, so a
        # commit that yielded any event at all reported as fully read even when
        # another watched file had dropped rows on the floor.
        self._commit("requirements.md", REQS_ONE, "one requirement")
        (self.root / "docs" / "engagement" / "requirements.md").write_text(REQS_TWO)
        (self.root / "docs" / "engagement" / "tasks.md").write_text(
            TASKS_HEADER_ONLY + "| T1 | A | R1 | nonsense-status | x |\n"
        )
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "real requirement plus a broken task row")

        feed = serve.build_feed(self.root)
        self.assertIn("req.added", [e.kind for e in feed.events])
        self.assertGreaterEqual(feed.unreadable, 1)

    def test_non_repo_signals_history_not_ok(self):
        with tempfile.TemporaryDirectory() as plain:
            feed = serve.build_feed(Path(plain))
            self.assertFalse(feed.history_ok)
            self.assertEqual(feed.events, ())

    def test_feed_is_capped_and_reports_the_remainder(self):
        # The cap is injectable so this proves the truncation logic with a
        # handful of commits instead of hundreds of real `git` calls: the
        # logic is identical at 5 as at 200, and this way the test cannot go
        # flaky under machine load the way 200+ real commits can.
        for index in range(6):
            rows = "".join(
                f"| T{n} | task {n} | R1 | (unassigned) | done | x |\n" for n in range(index + 1)
            )
            self._commit("tasks.md", TASKS_HEADER_ONLY + rows, f"c{index}")
        feed = serve.build_feed(self.root, cap=5)
        self.assertEqual(len(feed.events), 5)
        self.assertEqual(feed.truncated, 1)

    def test_feed_cap_default_is_200(self):
        # Cheap guard against accidentally lowering the production default.
        self.assertEqual(serve.FEED_CAP, 200)

    def test_cached_feed_does_not_rebuild_without_a_new_commit(self):
        self._commit("tasks.md", TASKS_HEADER_ONLY, "one")
        serve._feed_cache.clear()
        first = serve.cached_feed(self.root)
        (self.root / "docs" / "engagement" / "tasks.md").write_text(
            TASKS_HEADER_ONLY + "| T9 | uncommitted | R1 | (unassigned) | todo | x |\n"
        )
        self.assertIs(serve.cached_feed(self.root), first)

    def test_criterion_change_in_the_same_commit_as_its_own_signoff_is_not_drift(self):
        # A sign-off approves requirements.md AS AT the commit that records it.
        # Changing a criterion in that SAME commit is part of what was
        # approved, not a violation of it — so it must not read as scope
        # drift, no matter which file git happens to list first.
        self._commit("requirements.md", REQS_ONE, "add requirement")
        (self.root / "docs" / "engagement" / "requirements.md").write_text(REQS_ONE_CHANGED)
        (self.root / "docs" / "engagement" / "signoffs.md").write_text(SIGNOFF_ONE)
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "change criterion and sign off together")

        feed = serve.build_feed(self.root)
        criterion_events = [e for e in feed.events if e.kind == "req.criterion"]
        self.assertEqual(len(criterion_events), 1)
        self.assertEqual(criterion_events[0].tone, "progress")

    def test_criterion_change_after_signoff_in_a_later_commit_is_still_drift(self):
        self._commit("requirements.md", REQS_ONE, "add requirement")
        self._commit("signoffs.md", SIGNOFF_ONE, "sign off requirements")
        self._commit("requirements.md", REQS_ONE_CHANGED, "change criterion later")

        feed = serve.build_feed(self.root)
        criterion_events = [e for e in feed.events if e.kind == "req.criterion"]
        self.assertEqual(len(criterion_events), 1)
        self.assertEqual(criterion_events[0].tone, "scope")

    def test_requirements_are_diffed_before_signoffs_are_absorbed_even_when_git_lists_them_reversed(self):
        # Regression guard for the processing-order fix. A prior version of
        # this test asserted `_PROCESS_ORDER`'s declared order against
        # itself and never checked that `build_feed` actually consults it —
        # a re-reviewer proved that by reverting the enforcement at the
        # `serve.py` call site (back to bare `for path in paths:`) while
        # leaving `_PROCESS_ORDER` in place, and all of that test's
        # assertions still passed. This one drives `build_feed` end to end
        # with git mocked out and an ADVERSARIAL path order — signoffs.md
        # listed before requirements.md, as if that were what git returned
        # for a commit that changes a criterion and signs it off together —
        # so it fails if the enforcement is ever dropped, even though the
        # constant is still declared correctly.
        commits = (
            ("s1", "2026-01-01T00:00:00+00:00", ("docs/engagement/requirements.md",)),
            (
                "s2",
                "2026-01-02T00:00:00+00:00",
                # Adversarial order: signoffs.md before requirements.md.
                ("docs/engagement/signoffs.md", "docs/engagement/requirements.md"),
            ),
        )
        contents = {
            ("s1", "docs/engagement/requirements.md"): REQS_ONE,
            ("s2", "docs/engagement/requirements.md"): REQS_ONE_CHANGED,
            ("s2", "docs/engagement/signoffs.md"): SIGNOFF_ONE,
        }

        def fake_file_at(root, sha, path):
            return True, contents[(sha, path)]

        patched_commits = unittest.mock.patch.object(
            history, "engagement_commits", return_value=(True, commits)
        )
        patched_file_at = unittest.mock.patch.object(
            history, "file_at", side_effect=fake_file_at
        )
        self.addCleanup(patched_commits.stop)
        self.addCleanup(patched_file_at.stop)
        patched_commits.start()
        patched_file_at.start()

        feed = serve.build_feed(self.root)
        criterion_events = [e for e in feed.events if e.kind == "req.criterion"]
        self.assertEqual(len(criterion_events), 1)
        # With enforcement: requirements.md is diffed first, `signed` is
        # still empty at that point, so this reads as ordinary drafting —
        # not scope drift against a baseline that was never actually signed
        # before the change happened.
        self.assertEqual(criterion_events[0].tone, "progress")
        self.assertNotIn("after", criterion_events[0].text.lower())


class TestFeedRender(unittest.TestCase):
    def _state_with(self, feed):
        return _state(feed=feed)

    def test_each_event_becomes_a_row_carrying_its_commit_and_date(self):
        feed = Feed((Event("2026-08-16T10:00:00+00:00", "abc1234", "task.status",
                           "T1", "T1 todo → done", "milestone"),), 3, 0, True, 0)
        html = render._feed(self._state_with(feed))
        self.assertIn('data-commit="abc1234"', html)
        self.assertIn('data-when="2026-08-16', html)
        self.assertIn("T1 todo → done", html)

    def test_no_git_says_so_and_renders_no_rows(self):
        html = render._feed(self._state_with(Feed((), 0, 0, False, 0)))
        self.assertIn("no history available", html.lower())
        self.assertNotIn("gf-ev", html)

    def test_no_commits_is_distinct_from_no_git(self):
        html = render._feed(self._state_with(Feed((), 0, 0, True, 0)))
        self.assertIn("no engagement history yet", html.lower())
        self.assertNotIn("no history available", html.lower())

    def test_unreadable_commits_are_named_in_the_footnote(self):
        feed = Feed((), 24, 1, True, 0)
        html = render._feed(self._state_with(feed))
        self.assertIn("24", html)
        self.assertIn("1", html)
        self.assertIn("may be missing", html.lower())

    def test_truncation_states_the_remainder(self):
        # events must be non-empty: the footnote total is
        # len(feed.events) + feed.truncated, and with an empty events tuple
        # that expression is indistinguishable from a bug that reports
        # feed.truncated alone — both would render "300". 3 events with
        # truncated=297 makes the two formulas disagree (300 vs 297), so a
        # regression that drops the retained-events term actually fails.
        events = tuple(
            Event(f"2026-08-{10 + i:02d}", f"abc000{i}", "task.status", "T1",
                  f"event {i}", "progress")
            for i in range(3)
        )
        feed = Feed(events, 500, 0, True, 297)
        html = render._feed(self._state_with(feed))
        self.assertIn("showing 3 most recent of 300", html)

    def test_feed_is_wired_into_the_full_page_body(self):
        # Step-6 regression: _feed() was fully built and tested in isolation
        # (every other test in this class calls render._feed() directly) but
        # body() never called it, so the Activity card never reached the
        # actual page. No prior test drove render.body() and looked for the
        # feed, so nothing caught this. Assert it here, through body().
        feed = Feed((Event("2026-08-16T10:00:00+00:00", "abc1234", "task.status",
                           "T1", "T1 todo → done", "milestone"),), 1, 0, True, 0)
        html = render.body(self._state_with(feed))
        self.assertIn('id="gf-feed"', html)
        self.assertIn('data-commit="abc1234"', html)
        self.assertIn("Activity", html)

    def test_client_hooks_are_present(self):
        # render.FEED_JS finds rows via data-when / data-commit and writes
        # into #gf-feedcount / moves #gf-earlier. Nothing here would fail if
        # they were deleted as "unused markup", so this test is the guard
        # against that.
        feed = Feed((Event("2026-08-16T10:00:00+00:00", "abc1234", "task.status",
                           "T1", "T1 todo → done", "milestone"),), 1, 0, True, 0)
        html = render._feed(self._state_with(feed))
        self.assertIn('data-when="2026-08-16T10:00:00+00:00"', html)
        self.assertIn('data-commit="abc1234"', html)
        self.assertIn('id="gf-feedcount"', html)
        self.assertIn('<div class="gf-fdiv hide" id="gf-earlier">earlier</div>', html)

    def test_range_toggle_buttons_are_present(self):
        # Step-6 regression: FEED_JS's click handler binds to
        # [data-range] buttons, but nothing in this file emitted them --
        # there was no markup for "7 days" / "All" / "Since last visit" to
        # click on. Only surfaced by driving the real page; pinned here so
        # it cannot silently regress again.
        # Asserted on the whole page, not on _feed's fragment. The original
        # version checked _feed alone, and that is precisely how the page came
        # to serve TWO complete chip groups: the layout rework moved them into
        # _topbar without removing this copy, and a test that only looked
        # inside _feed stayed green throughout. Counting on the assembled page
        # is the assertion that catches both a missing set and a duplicated
        # one.
        html = render.body(_state())
        for value in ("7", "all", "visit"):
            self.assertEqual(
                html.count('data-range="%s"' % value), 1,
                "expected exactly one data-range=%r control on the page" % value,
            )
        self.assertEqual(html.count('aria-label="Time range"'), 1)

    def test_footnote_states_unreadable_and_truncation_together(self):
        # The realistic shape for a long engagement: some events shown, some
        # commits unreadable, and some events truncated — all three facts
        # must appear in one footnote sentence, not just whichever was
        # tested last.
        events = tuple(
            Event(f"2026-08-{10 + i:02d}", f"abc000{i}", "task.status", "T1",
                  f"event {i}", "progress")
            for i in range(2)
        )
        feed = Feed(events, 50, 4, True, 44)
        html = render._feed(self._state_with(feed))
        self.assertIn(
            "50 commits scanned \u00b7 4 could not be read, so events may be "
            "missing \u00b7 showing 2 most recent of 46",
            html,
        )

    def test_event_text_is_escaped(self):
        feed = Feed((Event("2026-08-16", "abc", "task.added", "T1",
                           "<script>alert(1)</script>", "progress"),), 1, 0, True, 0)
        html = render._feed(self._state_with(feed))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


class TestFeedScript(unittest.TestCase):
    """The Python suite has no JS runtime — it cannot execute FEED_JS or
    prove its comparisons behave correctly. What follows only pins that the
    script's source text references the attributes/ids the markup carries,
    and that the script is wired into the page. The behaviour itself is
    verified by hand (see task-9-report.md, Step 6)."""

    def test_hide_rule_is_not_written_per_element(self):
        # C1. FEED_JS toggles `hide` on .gf-ev, .gf-fdiv AND .gf-tk, but the
        # CSS carried one rule per element and .gf-tk was never added — the
        # task filter was inert while its chip said the filter was applied.
        # A per-element rule has to be remembered every time the script
        # learns to hide something new, and it was not. Only a rule that
        # hides any descendant closes the class of defect.
        self.assertRegex(
            render.CSS,
            r"(?:^|[\s,>])\.hide\s*\{[^}]*display\s*:\s*none",
        )

    def test_every_class_the_script_toggles_has_a_css_rule(self):
        # The static half of the client-script gap: this suite has no JS
        # runtime, but the classes the script names are readable text, and
        # so is the stylesheet. A toggled class with no rule is a no-op the
        # UI presents as an applied filter.
        toggled = set(re.findall(
            r"classList\.(?:toggle|add|remove)\('([A-Za-z0-9_-]+)'", render.FEED_JS))
        self.assertTrue(toggled, "found no toggled classes — the regex has rotted")
        for cls in sorted(toggled):
            self.assertRegex(
                render.CSS,
                r"(?:^|[\s,>{])\.(?:[A-Za-z0-9_-]+\.)*" + re.escape(cls) + r"\s*[,{\s]",
                "FEED_JS toggles ." + cls + " but no CSS rule defines it",
            )

    def test_no_chip_is_marked_on_before_the_script_applies_a_filter(self):
        # I5. `on` means "this is what you are looking at". The server
        # renders every row unfiltered and cannot know what "since your last
        # visit" means for this browser, so with JS disabled, blocked, or
        # throwing before start(), a server-rendered `on` chip sat above the
        # engagement's whole history asserting a filter nothing had applied.
        self.assertNotIn("gf-chip on", render.body(_state()))
        self.assertIn("markOn", render.FEED_JS)

    def test_script_reads_the_attributes_the_markup_writes(self):
        self.assertIn("data-commit", render.FEED_JS)
        self.assertIn("data-when", render.FEED_JS)
        self.assertIn("data-filter", render.FEED_JS)

    def test_rerender_reapplies_the_chosen_range_not_the_default(self):
        # The reader picks "All", then anyone commits: POLL_JS swaps #root and
        # fires gf:rendered, `start` runs again, and the page snapped back to
        # "Since last visit" mid-scroll — every two seconds on a busy day.
        # `start` must re-apply the CURRENT selection, which is the whole
        # reason it is bound to gf:rendered.
        self.assertIn("var curRange = 'visit', curFilter = 'all';", render.FEED_JS)
        self.assertIn("apply(curRange);", render.FEED_JS)
        self.assertIn("filterTasks(curFilter);", render.FEED_JS)
        self.assertIn("markOn('data-range', curRange);", render.FEED_JS)
        self.assertIn("markOn('data-filter', curFilter);", render.FEED_JS)
        # And the click handler must record the choice, or the above re-applies
        # a value that never changes.
        self.assertIn("curRange = chip.getAttribute('data-range');", render.FEED_JS)
        self.assertIn("curFilter = chip.getAttribute('data-filter');", render.FEED_JS)
        # start() must not hardcode either default; if it does, the choice is
        # discarded on the next poll no matter what the click handler recorded.
        start = render.FEED_JS[render.FEED_JS.index("function start()"):]
        start = start[:start.index("\n  }")]
        self.assertNotIn("'visit'", start)
        self.assertNotIn("'all'", start)

    def test_script_persists_and_reads_the_last_seen_commit(self):
        self.assertIn("localStorage", render.FEED_JS)

    def test_first_visit_message_is_present(self):
        self.assertIn("No previous visit recorded", render.FEED_JS)

    def test_script_is_included_in_the_page(self):
        self.assertIn(render.FEED_JS, render.page(_state()))

    def test_localstorage_read_and_write_are_each_wrapped_in_try_except(self):
        # Honest-failure rule: localStorage can throw (private browsing,
        # disabled storage). Both the read and the write must be guarded, or
        # a throw produces an unhandled JS error instead of falling back to
        # the 7-day window.
        self.assertIn("try { return localStorage.getItem(KEY); } catch (e)", render.FEED_JS)
        self.assertIn("try { localStorage.setItem(KEY, commit); } catch (e)", render.FEED_JS)

    def test_script_listens_for_gf_rendered_like_theme_js_does(self):
        # POLL_JS replaces #root's innerHTML on every poll and dispatches
        # gf:rendered afterwards. FEED_JS must re-apply itself on that event,
        # the same pattern THEME_JS uses (asserted below), or every poll
        # would silently reset the visitor's chosen range/filter.
        self.assertIn("document.addEventListener('gf:rendered', start)", render.FEED_JS)
        self.assertIn("document.addEventListener('gf:rendered'", render.THEME_JS)

    def test_script_wires_a_click_handler_to_both_range_and_filter_chips(self):
        self.assertIn("data-range", render.FEED_JS)
        self.assertIn("event.target.closest", render.FEED_JS)

    def test_script_names_the_nomatch_hook_it_unhides(self):
        self.assertIn("gf-nomatch", render.FEED_JS)

    def test_script_names_the_earlier_divider_it_moves(self):
        self.assertIn("gf-earlier", render.FEED_JS)

    def test_script_writes_the_feedcount_label(self):
        self.assertIn("gf-feedcount", render.FEED_JS)

    def test_script_does_not_default_the_task_list_to_a_single_status(self):
        # Step-6 regression: the script initially called filterTasks('blocked')
        # on load. Server-rendered HTML shows every task; silently hiding
        # everything but "blocked" the moment JS runs -- with no chip marked
        # active to explain why -- is exactly the "confident empty view" the
        # honest-failure rules forbid. The default must match what the
        # no-JS page already shows: everything.
        #
        # The default now lives in `curFilter`'s initialiser rather than a
        # literal call, so that a re-render re-applies the reader's choice
        # instead of resetting it. The requirement is unchanged: whatever the
        # script applies first must be "all".
        self.assertIn("curFilter = 'all'", render.FEED_JS)
        self.assertIn("filterTasks(curFilter);", render.FEED_JS)
        self.assertNotIn("filterTasks('blocked')", render.FEED_JS)
        self.assertNotIn("curFilter = 'blocked'", render.FEED_JS)
