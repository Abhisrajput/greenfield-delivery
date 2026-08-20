"""Dataclasses shared by the pure layers. No logic lives here."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    """Something the parser could not read. Never raised — always returned."""

    file: str
    line: int | None
    message: str


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    req: str
    # Written by /sync-tracker from the tracker's assignee, never maintained by
    # hand. "(unassigned)" rather than blank: a blank cell conflates "nobody is
    # on this" with "nobody filled it in", and on a team those are different
    # problems.
    owner: str
    status: str
    item: str
    line: int


@dataclass(frozen=True)
class TaskFile:
    """Three distinct states, so callers cannot conflate them:

    absent          present=False
    unreadable      present=True,  header_ok=False
    valid           present=True,  header_ok=True (tasks may be empty)
    """

    present: bool
    header_ok: bool
    tasks: tuple[Task, ...]
    problems: tuple[Problem, ...]


@dataclass(frozen=True)
class TestCase:
    id: str
    req: str          # exactly one R<n>/N<n>; never blank, never "none"
    mode: str         # "manual" | "automated" — a delivery decision, stated
    scenario: str
    given: str
    when: str
    then: str
    result: str       # one of TEST_RESULTS
    line: int


@dataclass(frozen=True)
class TestCaseFile:
    present: bool
    header_ok: bool
    cases: tuple["TestCase", ...]
    problems: tuple["Problem", ...]


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    criterion: str
    kind: str  # "functional" | "non-functional" | "out-of-scope"


@dataclass(frozen=True)
class RequirementsFile:
    present: bool
    requirements: tuple[Requirement, ...]
    problems: tuple[Problem, ...]


@dataclass(frozen=True)
class Engagement:
    client: str
    tracker_type: str
    project: str
    epic: str
    narrative: str
    dashboard_url: str


@dataclass(frozen=True)
class EngagementFile:
    present: bool
    engagement: "Engagement | None"
    problems: tuple[Problem, ...]


@dataclass(frozen=True)
class Signoff:
    gate: str
    artifact: str
    commit: str
    approved_by: str
    date: str
    evidence: str
    line: int


@dataclass(frozen=True)
class SignoffFile:
    present: bool
    header_ok: bool
    signoffs: tuple[Signoff, ...]
    problems: tuple[Problem, ...]


@dataclass(frozen=True)
class Counts:
    done: int = 0
    in_progress: int = 0
    blocked: int = 0
    todo: int = 0
    dropped: int = 0

    @property
    def total_active(self) -> int:
        """Everything except dropped. Dropped work is not part of the denominator."""
        return self.done + self.in_progress + self.blocked + self.todo

    @property
    def remaining(self) -> int:
        return self.in_progress + self.blocked + self.todo


@dataclass(frozen=True)
class CoverageRow:
    requirement: "Requirement"
    tasks: tuple["Task", ...]
    counts: Counts


SEVERITY_ORDER = ("critical", "serious", "warning")


@dataclass(frozen=True)
class Finding:
    severity: str
    label: str
    detail: str


@dataclass(frozen=True)
class TrendPoint:
    date: str
    remaining: int | None  # None when the revision could not be parsed
    readable: bool


@dataclass(frozen=True)
class Trend:
    points: tuple[TrendPoint, ...]
    readable: int
    unreadable: int
    history_ok: bool  # False when git itself could not be read — distinct
    # from "read git successfully, found no history"


@dataclass(frozen=True)
class Gate:
    name: str
    artifact: str
    # "changed" and "unverifiable" are NOT the same failure and must not be
    # merged: "changed" means the commit is present and the artifact moved
    # since it (scope drift against a signed baseline); "unverifiable"
    # means the commit or the path could not be found at all.
    state: str  # "approved" | "current" | "pending" | "changed" | "unverifiable"
    date: str
    commit: str


EVENT_TONES = ("milestone", "scope", "attention", "progress")


@dataclass(frozen=True)
class Event:
    """A change to the engagement, derived from one commit."""

    when: str      # ISO date from the commit
    commit: str
    kind: str      # "task.status", "req.criterion", ... — drives filtering
    subject: str   # "T4", "R7", "Design" — what the event is about
    text: str      # human-readable, already assembled
    tone: str      # one of EVENT_TONES — drives colour


@dataclass(frozen=True)
class Feed:
    events: tuple["Event", ...]   # newest first
    scanned: int                  # commits examined
    unreadable: int               # commits whose files would not parse
    history_ok: bool              # False when git itself could not be read
    truncated: int                # events beyond the cap, not returned


@dataclass(frozen=True)
class Decision:
    id: str
    date: str
    decision: str
    why: str
    instead_of: str
    decided_by: str
    line: int


@dataclass(frozen=True)
class DecisionFile:
    present: bool
    header_ok: bool
    decisions: tuple["Decision", ...]
    problems: tuple["Problem", ...]


@dataclass(frozen=True)
class Drift:
    """What changed in an approved artifact since the commit it was approved at.

    `lines` is None when the comparison could not be made — git unreadable, or
    the file absent from one side. None is "cannot tell", never "no changes":
    an empty diff and an unavailable diff are opposite claims about whether the
    client's approval still covers the file.
    """

    artifact: str
    commit: str
    lines: "tuple[str, ...] | None"
    truncated: int = 0
    why: str = ""


@dataclass(frozen=True)
class State:
    engagement: "EngagementFile"
    reqs: "RequirementsFile"
    tasks: "TaskFile"
    signoffs: "SignoffFile"
    signoff_status: "dict[tuple[str, str], str]"  # (commit, artifact) -> status
    findings: tuple["Finding", ...]
    trend: "Trend"
    gates: tuple[Gate, ...]
    is_repo: bool
    # Honest defaults, not convenient ones: a repo with no history genuinely
    # produces this empty Feed, and None already means "cannot tell"
    # everywhere else in this codebase.
    feed: "Feed" = Feed((), 0, 0, True, 0)
    days_in_gate: "int | None" = None
    days_since_commit: "int | None" = None
    drift: tuple["Drift", ...] = ()
