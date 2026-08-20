"""Markdown to models.

Every function is pure and total: no I/O, no clock, no exceptions. A file that
cannot be read returns problems alongside whatever was readable. Nothing here
may guess at a value it did not find.
"""

from __future__ import annotations

from .model import (
    Decision,
    DecisionFile,
    TestCase,
    TestCaseFile,
    Engagement,
    EngagementFile,
    Problem,
    Requirement,
    RequirementsFile,
    Signoff,
    SignoffFile,
    Task,
    TaskFile,
)

TASKS_FILE = "tasks.md"
TASKS_HEADER = ("ID", "Task", "Req", "Owner", "Status", "Item")
TASK_STATUSES = frozenset({"todo", "in-progress", "blocked", "done", "dropped"})


def _cells(line: str) -> list[str] | None:
    """Split a markdown table row into cells, or None if it is not one."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _is_divider(cells: list[str]) -> bool:
    return all(set(cell) <= set("-: ") and cell for cell in cells)


def parse_tasks(text: str | None) -> TaskFile:
    if text is None:
        return TaskFile(present=False, header_ok=False, tasks=(), problems=())

    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines):
        cells = _cells(line)
        if cells is not None and tuple(cells) == TASKS_HEADER:
            header_index = index
            break

    if header_index is None:
        expected = "| " + " | ".join(TASKS_HEADER) + " |"
        return TaskFile(
            present=True,
            header_ok=False,
            tasks=(),
            problems=(
                Problem(
                    TASKS_FILE,
                    None,
                    f"header not recognised — expected exactly: {expected}",
                ),
            ),
        )

    tasks: list[Task] = []
    problems: list[Problem] = []

    for offset, line in enumerate(lines[header_index + 1 :], start=header_index + 2):
        cells = _cells(line)
        if cells is None:
            if line.strip():
                break  # table has ended
            continue
        if len(cells) != len(TASKS_HEADER):
            problems.append(
                Problem(
                    TASKS_FILE,
                    offset,
                    f"expected {len(TASKS_HEADER)} cells, found {len(cells)}",
                )
            )
            continue

        if _is_divider(cells):
            continue

        task_id, title, req, owner, status, item = cells

        if not req:
            problems.append(
                Problem(TASKS_FILE, offset, "Req is blank — write 'none' if unlinked")
            )
            continue
        if status not in TASK_STATUSES:
            allowed = ", ".join(sorted(TASK_STATUSES))
            problems.append(
                Problem(
                    TASKS_FILE, offset, f"unknown status {status!r} — expected one of: {allowed}"
                )
            )
            continue
        if not owner:
            problems.append(
                Problem(TASKS_FILE, offset,
                        "Owner is blank — write '(unassigned)' if nobody is on it")
            )
            continue
        if not task_id or not title or not item:
            problems.append(Problem(TASKS_FILE, offset, "ID, Task and Item must not be blank"))
            continue

        tasks.append(Task(task_id, title, req, owner, status, item, offset))

    return TaskFile(
        present=True,
        header_ok=True,
        tasks=tuple(tasks),
        problems=tuple(problems),
    )


DECISIONS_FILE = "decisions.md"
DECISIONS_HEADER = ("ID", "Date", "Decision", "Why", "Instead of", "Decided by")


def parse_decisions(text: str | None) -> DecisionFile:
    if text is None:
        return DecisionFile(present=False, header_ok=False, decisions=(), problems=())

    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines):
        cells = _cells(line)
        if cells is not None and tuple(cells) == DECISIONS_HEADER:
            header_index = index
            break
    if header_index is None:
        expected = "| " + " | ".join(DECISIONS_HEADER) + " |"
        return DecisionFile(
            present=True, header_ok=False, decisions=(),
            problems=(Problem(DECISIONS_FILE, None,
                              f"header not recognised — expected exactly: {expected}"),),
        )

    decisions: list[Decision] = []
    problems: list[Problem] = []
    for offset, line in enumerate(lines[header_index + 1:], start=header_index + 2):
        cells = _cells(line)
        if cells is None:
            if line.strip():
                break
            continue
        if len(cells) != len(DECISIONS_HEADER):
            problems.append(Problem(DECISIONS_FILE, offset,
                                    f"expected {len(DECISIONS_HEADER)} cells, found {len(cells)}"))
            continue
        if _is_divider(cells):
            continue

        ident, date, decision, why, instead, by = cells
        if not why.strip():
            # The reason is the entire artifact. A row without one is a
            # constraint with no justification, and the next team deletes it.
            problems.append(Problem(DECISIONS_FILE, offset,
                                    f"{ident or 'row'} has no 'Why' — the reason is the point"))
            continue
        if not ident or not decision.strip():
            problems.append(Problem(DECISIONS_FILE, offset,
                                    "ID and Decision must not be blank"))
            continue
        decisions.append(Decision(ident, date, decision, why, instead, by, offset))

    return DecisionFile(present=True, header_ok=True,
                        decisions=tuple(decisions), problems=tuple(problems))


TESTS_FILE = "test-cases.md"
TESTS_HEADER = ("ID", "Req", "Mode", "Scenario", "Given", "When", "Then", "Result")
# Whether a case is automated is a DELIVERY decision and is stated, never
# inferred from whether a feature file happens to exist. Inferring it makes
# "nobody wired this up yet" and "this is deliberately run by a person"
# indistinguishable, and creates quiet pressure to automate requirements
# that cannot honestly be automated at all.
TEST_MODES = {"manual", "automated"}
# "not run" is the honest default and a real value, not the absence of one. A
# blank Result would conflate "nobody has tried this" with "this passed", and
# at handoff those are opposite claims.
TEST_RESULTS = {"not run", "pass", "fail", "blocked"}


def parse_test_cases(text: str | None) -> TestCaseFile:
    if text is None:
        return TestCaseFile(present=False, header_ok=False, cases=(), problems=())

    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines):
        cells = _cells(line)
        if cells is not None and tuple(cells) == TESTS_HEADER:
            header_index = index
            break

    if header_index is None:
        expected = "| " + " | ".join(TESTS_HEADER) + " |"
        return TestCaseFile(
            present=True, header_ok=False, cases=(),
            problems=(Problem(TESTS_FILE, None,
                              f"header not recognised — expected exactly: {expected}"),),
        )

    cases: list[TestCase] = []
    problems: list[Problem] = []
    for offset, line in enumerate(lines[header_index + 1:], start=header_index + 2):
        cells = _cells(line)
        if cells is None:
            if line.strip():
                break
            continue
        if len(cells) != len(TESTS_HEADER):
            problems.append(Problem(TESTS_FILE, offset,
                                    f"expected {len(TESTS_HEADER)} cells, found {len(cells)}"))
            continue
        if _is_divider(cells):
            continue

        case_id, req, mode, scenario, given, when, then, result = cells

        if not req:
            problems.append(Problem(TESTS_FILE, offset, "Req is blank"))
            continue
        if req.lower() == "none":
            # Deliberately stricter than tasks.md, which permits `none`. A case
            # tracing to no requirement tests something the client never
            # approved — either a missing requirement or work that should not
            # be happening. Both need raising, not filing under a placeholder.
            problems.append(Problem(TESTS_FILE, offset,
                                    "Req is 'none' — every test case must trace to a requirement"))
            continue
        if mode not in TEST_MODES:
            allowed = ", ".join(sorted(TEST_MODES))
            problems.append(Problem(TESTS_FILE, offset,
                                    f"unknown mode {mode!r} — expected one of: {allowed}"))
            continue
        if result not in TEST_RESULTS:
            allowed = ", ".join(sorted(TEST_RESULTS))
            problems.append(Problem(TESTS_FILE, offset,
                                    f"unknown result {result!r} — expected one of: {allowed}"))
            continue
        if not case_id or not scenario or not then:
            problems.append(Problem(TESTS_FILE, offset,
                                    "ID, Scenario and Then must not be blank"))
            continue

        cases.append(TestCase(case_id, req, mode, scenario, given, when, then, result, offset))

    return TestCaseFile(present=True, header_ok=True,
                        cases=tuple(cases), problems=tuple(problems))


REQS_FILE = "requirements.md"
_SECTION_KINDS = {
    "functional": "functional",
    "non-functional": "non-functional",
    "out of scope": "out-of-scope",
}


def parse_requirements(text: str | None) -> RequirementsFile:
    if text is None:
        return RequirementsFile(present=False, requirements=(), problems=())

    requirements: list[Requirement] = []
    problems: list[Problem] = []
    kind: str | None = None
    saw_section = False

    for index, line in enumerate(text.splitlines(), start=1):
        heading = line.strip().lower()
        if heading.startswith("## "):
            kind = _SECTION_KINDS.get(heading[3:].strip())
            saw_section = saw_section or kind is not None
            continue

        if kind is None:
            continue

        cells = _cells(line)
        if cells is None:
            continue
        if len(cells) != 3:
            problems.append(
                Problem(REQS_FILE, index, f"expected 3 cells, found {len(cells)}")
            )
            continue
        if _is_divider(cells):
            continue
        identifier, body, note = cells
        if identifier in ("#", "") or not identifier[0].isalpha():
            continue
        if identifier.lower() == "id":
            # The section's own header row. `_is_divider` catches the |---|
            # line under it, but nothing caught the header itself: "ID" starts
            # with a letter, so it was admitted as a requirement. Every real
            # identifier is R<n>, N<n> or X<n>, so a bare "ID" can only be the
            # header.
            #
            # This was not cosmetic. Each phantom had no tasks pointing at it,
            # so a well-formed requirements.md with three sections produced
            # CRITICAL findings reading "ID has no tasks — unplanned work",
            # and inflated the coverage denominator by three. Found by the
            # sample engagement in examples/, on a file with no defects in it.
            continue

        requirements.append(Requirement(identifier, body, note, kind))

    if not saw_section:
        problems.append(
            Problem(
                REQS_FILE,
                None,
                "no '## Functional', '## Non-functional' or '## Out of scope' section found",
            )
        )

    return RequirementsFile(
        present=True,
        requirements=tuple(requirements),
        problems=tuple(problems),
    )


ENGAGEMENT_FILE = "engagement.md"
SIGNOFFS_FILE = "signoffs.md"
SIGNOFFS_HEADER = ("Gate", "Artifact", "Commit", "Approved by", "Date", "Evidence")
PENDING = "(pending)"


def _block_fields(lines: list[str], heading: str) -> tuple[bool, dict[str, str]]:
    """Read `- key: value` bullets under a `## heading`.

    Returns `(seen, fields)` — whether the heading itself was found, kept
    separate from which fields it held. A block that exists but omits one
    expected field must not read the same as the block never existing.
    """
    fields: dict[str, str] = {}
    seen = False
    inside = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            inside = stripped[3:].strip().lower() == heading.lower()
            seen = seen or inside
            continue
        if inside and stripped.startswith("- ") and ":" in stripped:
            key, _, value = stripped[2:].partition(":")
            fields[key.strip().lower()] = value.strip()
    return seen, fields


def parse_engagement(text: str | None) -> EngagementFile:
    if text is None:
        return EngagementFile(present=False, engagement=None, problems=())

    lines = text.splitlines()
    problems: list[Problem] = []

    client = ""
    for line in lines:
        if line.startswith("# Engagement:"):
            client = line.split(":", 1)[1].strip()
            break
    if not client:
        problems.append(Problem(ENGAGEMENT_FILE, None, "no '# Engagement: <client>' title"))

    tracker_seen, tracker = _block_fields(lines, "Tracker")
    reporting_seen, reporting = _block_fields(lines, "Progress reporting")
    if not tracker_seen:
        problems.append(Problem(ENGAGEMENT_FILE, None, "no '## Tracker' block"))
    elif "epic" not in tracker:
        # `epic` gates the "tasks not yet in the tracker" finding — an absent
        # field here must not silently look the same as "no work item yet".
        problems.append(
            Problem(ENGAGEMENT_FILE, None, "'## Tracker' block has no 'epic:' field")
        )
    if not reporting_seen:
        problems.append(Problem(ENGAGEMENT_FILE, None, "no '## Progress reporting' block"))
    elif "narrative" not in reporting:
        # `narrative` gates the staleness check — an absent field here must
        # not silently disable it the same way `reporting: {}` conflates
        # "no block" with "block, but incomplete".
        problems.append(
            Problem(
                ENGAGEMENT_FILE,
                None,
                "'## Progress reporting' block has no 'narrative:' field",
            )
        )

    engagement = Engagement(
        client=client,
        tracker_type=tracker.get("type", ""),
        project=tracker.get("project", ""),
        epic=tracker.get("epic", ""),
        narrative=reporting.get("narrative", ""),
        dashboard_url=reporting.get("dashboard", ""),
    )
    return EngagementFile(present=True, engagement=engagement, problems=tuple(problems))


def parse_signoffs(text: str | None) -> SignoffFile:
    if text is None:
        return SignoffFile(present=False, header_ok=False, signoffs=(), problems=())

    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines):
        cells = _cells(line)
        if cells is not None and tuple(cells) == SIGNOFFS_HEADER:
            header_index = index
            break

    if header_index is None:
        expected = "| " + " | ".join(SIGNOFFS_HEADER) + " |"
        return SignoffFile(
            present=True,
            header_ok=False,
            signoffs=(),
            problems=(
                Problem(
                    SIGNOFFS_FILE,
                    None,
                    f"header not recognised — expected exactly: {expected}",
                ),
            ),
        )

    signoffs: list[Signoff] = []
    problems: list[Problem] = []

    for offset, line in enumerate(lines[header_index + 1 :], start=header_index + 2):
        cells = _cells(line)
        if cells is None:
            if line.strip():
                break  # table has ended
            continue
        if len(cells) != len(SIGNOFFS_HEADER):
            problems.append(
                Problem(
                    SIGNOFFS_FILE,
                    offset,
                    f"expected {len(SIGNOFFS_HEADER)} cells, found {len(cells)}",
                )
            )
            continue

        if _is_divider(cells):
            continue

        gate, artifact, commit, approved_by, date, evidence = cells
        if not commit:
            problems.append(
                Problem(SIGNOFFS_FILE, offset, "Commit is blank — the approval cannot be verified")
            )
            continue

        signoffs.append(Signoff(gate, artifact, commit, approved_by, date, evidence, offset))

    return SignoffFile(
        present=True,
        header_ok=True,
        signoffs=tuple(signoffs),
        problems=tuple(problems),
    )
