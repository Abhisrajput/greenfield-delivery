"""Models to findings. Pure: no I/O, no clock, no git.

Anything needing the filesystem or git is computed elsewhere and passed in.
"""

from __future__ import annotations

from .model import (
    Counts,
    CoverageRow,
    Finding,
    RequirementsFile,
    SEVERITY_ORDER,
    Task,
    TaskFile,
    Trend,
    TrendPoint,
)
from .parse import parse_tasks

UNLINKED = "none"

# tasks.md is produced at gate 2 (Design). Before that gate is signed off every
# requirement legitimately has no tasks, so reporting each one as unplanned work
# fills the attention panel with false criticals from day one — which teaches a
# the reader to stop reading the panel, the one thing it must never do.
TASKS_GATE = "design"


def tasks_expected(signoffs) -> bool:
    """Should tasks.md contain rows yet?

    True once the Design gate has a sign-off row, because that is the gate that
    produces the task list. Verification state is deliberately not consulted: a
    sign-off that later became unverifiable still means the tasks were produced,
    so their absence is still a real finding.
    """
    return any(s.gate.strip().lower() == TASKS_GATE for s in signoffs.signoffs)


def count(tasks: tuple[Task, ...]) -> Counts:
    tally = {"done": 0, "in-progress": 0, "blocked": 0, "todo": 0, "dropped": 0}
    for task in tasks:
        if task.status in tally:
            tally[task.status] += 1
    return Counts(
        done=tally["done"],
        in_progress=tally["in-progress"],
        blocked=tally["blocked"],
        todo=tally["todo"],
        dropped=tally["dropped"],
    )


def coverage(reqs: RequirementsFile, tasks: TaskFile) -> tuple[CoverageRow, ...]:
    """One row per in-scope requirement. Out-of-scope entries are excluded —
    they are expected to have no tasks, so listing them as uncovered would be
    a false alarm.

    `tasks.header_ok` is False both when `tasks.md` is absent and when it is
    present but unreadable (e.g. a reordered header) — in either case
    `tasks.tasks` is `()`, and computing coverage from it would draw a
    confident "no tasks" for every requirement from a file we could not
    actually read. Callers must not treat an empty result here as "checked
    and found none"; `render.py` and `findings()` key off `tasks.present` /
    `tasks.header_ok` directly to say so explicitly."""
    if not tasks.header_ok:
        return ()
    rows = []
    for requirement in reqs.requirements:
        if requirement.kind == "out-of-scope":
            continue
        attached = tuple(t for t in tasks.tasks if t.req == requirement.id)
        rows.append(CoverageRow(requirement, attached, count(attached)))
    return tuple(rows)


def unlinked(tasks: TaskFile) -> tuple[Task, ...]:
    return tuple(t for t in tasks.tasks if t.req == UNLINKED)


def out_of_scope_tasks(reqs: RequirementsFile, tasks: TaskFile) -> tuple[Task, ...]:
    excluded = {r.id for r in reqs.requirements if r.kind == "out-of-scope"}
    return tuple(t for t in tasks.tasks if t.req in excluded)


def dangling(reqs: RequirementsFile, tasks: TaskFile) -> tuple[Task, ...]:
    """Tasks citing a requirement that does not exist. Only meaningful when a
    requirements file was actually read — otherwise every task looks dangling."""
    if not reqs.present:
        return ()
    known = {r.id for r in reqs.requirements}
    return tuple(t for t in tasks.tasks if t.req != UNLINKED and t.req not in known)


def current_signoffs(signoffs):
    """The sign-off that counts for each gate: the LAST row recorded for it.

    `signoffs.md` is append-only, so re-approving a gate after its artifact
    legitimately changed appends a second row rather than editing the first.
    That is the methodology's own remedy for drift — a change order, recorded.

    Re-checking every row forever meant a superseded approval stayed a live
    CRITICAL for the rest of the engagement, while `gates_from` (which already
    keyed by gate) showed the same gate as approved. The product contradicted
    itself about one gate at one moment, which is exactly the confident
    falsehood everything here is built to avoid.

    Superseded rows stay in the file and stay visible — they are the history of
    what moved. They are simply not re-checked as though they were current.
    """
    latest = {}
    for signoff in signoffs.signoffs:
        latest[signoff.gate.lower()] = signoff
    return tuple(latest.values())


def findings(
    engagement,
    reqs,
    tasks,
    signoffs,
    signoff_status: dict,
    status_age_days: int | None,
    cadence_days: int,
) -> tuple[Finding, ...]:
    """Assemble everything needing attention, most severe first.

    `signoff_status` maps (commit, artifact) -> "unchanged" | "changed" |
    "unverifiable", computed by `history` so this stays pure. Keying by the
    pair, not the commit alone, matters because one commit legitimately
    covers several artifacts (a gate that produces multiple files, signed
    off in one row each, all at the same SHA) — keying by commit alone would
    collapse those rows and let one artifact's status stand in for another's.
    `status_age_days` is None when the status page is not on disk — that is
    "cannot see", not "stale".
    """
    out: list[Finding] = []

    for signoff in current_signoffs(signoffs):
        state = signoff_status.get((signoff.commit, signoff.artifact), "unverifiable")
        if state == "changed":
            out.append(
                Finding(
                    "critical",
                    f"{signoff.artifact} changed after sign-off",
                    f"{signoff.artifact} was approved at {signoff.commit} for the "
                    f"{signoff.gate} gate; the file has changed since. The recorded "
                    f"approval no longer covers the current file.",
                )
            )
        elif state == "unverifiable":
            out.append(
                Finding(
                    "critical",
                    f"{signoff.artifact} sign-off cannot be checked",
                    f"Cannot verify: commit {signoff.commit} is not in this repository.",
                )
            )

    for task in out_of_scope_tasks(reqs, tasks):
        out.append(
            Finding(
                "critical",
                "Task on out-of-scope work",
                f"{task.id} cites {task.req}, which is an out-of-scope exclusion.",
            )
        )

    empty_but_valid = tasks.present and tasks.header_ok and not tasks.tasks
    if empty_but_valid and not tasks_expected(signoffs):
        pass  # Gate 2 has not run. No coverage conclusion is available yet.
    elif empty_but_valid:
        out.append(
            Finding(
                "critical",
                "Task list is empty",
                "The Design gate is signed off — that is the gate that produces "
                "tasks.md — but the file contains no tasks.",
            )
        )
    else:
        for row in coverage(reqs, tasks):
            if not row.tasks:
                out.append(
                    Finding(
                        "critical",
                        "Requirement with no tasks",
                        f"{row.requirement.id} has no tasks — unplanned work.",
                    )
                )

    unlinked_tasks = unlinked(tasks)
    if unlinked_tasks:
        out.append(
            Finding(
                "serious",
                "Tasks with no requirement",
                f"{', '.join(t.id for t in unlinked_tasks)} — possible scope creep.",
            )
        )

    blocked = [t for t in tasks.tasks if t.status == "blocked"]
    if blocked:
        out.append(
            Finding(
                "serious",
                "Blocked tasks",
                f"{', '.join(t.id for t in blocked)} are blocked.",
            )
        )

    dangling_tasks = dangling(reqs, tasks)
    if dangling_tasks:
        out.append(
            Finding(
                "serious",
                "Tasks citing an unknown requirement",
                ", ".join(f"{t.id} → {t.req}" for t in dangling_tasks),
            )
        )

    if status_age_days is not None and status_age_days > cadence_days:
        out.append(
            Finding(
                "warning",
                "Status page is stale",
                f"status.md is {status_age_days} days old; the agreed cadence is "
                f"{cadence_days} days.",
            )
        )

    epic = engagement.engagement.epic if engagement.engagement else ""
    if epic and epic != "(pending)":
        unpushed = [t for t in tasks.tasks if t.item == "(pending)"]
        if unpushed:
            out.append(
                Finding(
                    "warning",
                    "Tasks not yet in the tracker",
                    f"{', '.join(t.id for t in unpushed)} have no work item — "
                    f"run /sync-tracker.",
                )
            )

    for source in (engagement, reqs, tasks, signoffs):
        for problem in source.problems:
            where = f"line {problem.line}" if problem.line else "file"
            out.append(
                Finding(
                    "warning",
                    f"Could not read {problem.file}",
                    f"{problem.file} {where}: {problem.message}",
                )
            )

    return tuple(sorted(out, key=lambda f: SEVERITY_ORDER.index(f.severity)))


def trend(history_ok: bool, revisions: tuple[tuple[str, str], ...]) -> Trend:
    """Remaining tasks per committed revision of tasks.md.

    `history_ok` is False when `history.revisions` could not read git itself
    (as opposed to reading git successfully and finding no history for the
    path) — kept separate so the renderer can say "cannot read history"
    rather than the false positive "no committed history yet".

    A revision that will not parse becomes a point with remaining=None. The
    renderer draws a gap there. Interpolating across it would invent progress
    that never happened.
    """
    points: list[TrendPoint] = []
    readable = 0
    unreadable = 0

    for when, content in revisions:
        parsed = parse_tasks(content)
        if not parsed.header_ok:
            points.append(TrendPoint(when, None, False))
            unreadable += 1
            continue
        points.append(TrendPoint(when, count(parsed.tasks).remaining, True))
        readable += 1

    return Trend(
        points=tuple(points), readable=readable, unreadable=unreadable, history_ok=history_ok
    )
