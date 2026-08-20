"""Parsed file versions in, typed events out.

Pure: no I/O, no subprocess, no clock, no randomness. Every function takes
already-parsed file objects plus the commit's metadata, which is what makes
each event kind testable from two strings.
"""

from __future__ import annotations

from .model import Event

PENDING = "(pending)"


def _by_id(items) -> dict:
    return {item.id: item for item in items}


def readable(parsed) -> bool:
    """Is this parsed file version safe to diff against another?

    One predicate for every watched file, and deliberately strict: **any**
    problem at all makes the version unreadable, not just a header that was
    never found.

    A file that parses at the header level while dropping individual rows into
    `problems` is a file whose contents we do not actually know. Diffing
    against it fabricates events in both directions — a dropped row reads as a
    deletion (`req.removed`, a scope claim, out of a four-cell typo) and its
    return one commit later reads as a fresh addition (a second `task.added`
    for a task that never went away). Both render as confident statements
    about the engagement that no one wrote.

    `header_ok` is not consulted separately because it does not need to be:
    `parse_tasks` and `parse_signoffs` both record a problem when the header is
    unrecognised, so `problems` already subsumes it. Likewise `parse_engagement`
    records a problem for every block it could not read.

    The same predicate is what `serve._unparsed` negates to count a commit
    towards `feed.unreadable`, so a version this refuses to diff is always a
    version the footnote admits to. Silence and the count move together.
    """
    return bool(parsed.present) and not parsed.problems


def from_tasks(previous, current, when: str, commit: str) -> tuple[Event, ...]:
    """Events between two versions of tasks.md.

    `previous` is None for the first revision. An unreadable version on either
    side yields no events — the caller counts those commits separately, because
    a silently skipped commit looks like a quiet day.
    """
    if not readable(current):
        return ()
    if previous is not None and not readable(previous):
        return ()

    before = _by_id(previous.tasks) if previous is not None else {}
    after = _by_id(current.tasks)
    out: list[Event] = []

    for task_id, task in after.items():
        was = before.get(task_id)
        if was is None:
            out.append(
                Event(when, commit, "task.added", task_id,
                      f"{task_id} added — {task.title}", "progress")
            )
            continue
        if was.status != task.status:
            if task.status == "dropped":
                out.append(
                    Event(when, commit, "task.dropped", task_id,
                          f"{task_id} dropped from scope — {task.title}", "scope")
                )
            else:
                out.append(
                    Event(when, commit, "task.status", task_id,
                          f"{task_id} {was.status} → {task.status} — {task.title}",
                          "milestone" if task.status == "done" else "progress")
                )
        if was.item == PENDING and task.item != PENDING:
            out.append(
                Event(when, commit, "task.item", task_id,
                      f"{task_id} pushed to the tracker as {task.item}", "progress")
            )
    return tuple(out)


REQUIREMENTS_ARTIFACT = "requirements.md"


def from_requirements(previous, current, when: str, commit: str,
                      signed_artifacts) -> tuple[Event, ...]:
    """Events between two versions of requirements.md.

    A criterion changing AFTER requirements.md was signed off is scope drift
    against a signed baseline — the most expensive failure this methodology
    exists to catch, and one nothing else in the product can see. It takes the
    `scope` tone; the same edit before sign-off is ordinary drafting.
    """
    if not readable(current):
        return ()
    if previous is not None and not readable(previous):
        return ()

    before = {r.id: r for r in previous.requirements} if previous is not None else {}
    after = {r.id: r for r in current.requirements}
    if previous is not None and not before and not after:
        return ()
    signed = REQUIREMENTS_ARTIFACT in signed_artifacts
    out: list[Event] = []

    for req_id, req in after.items():
        was = before.get(req_id)
        if was is None:
            out.append(
                Event(when, commit, "req.added", req_id,
                      f"{req_id} added — {req.text}", "scope" if signed else "progress")
            )
            continue
        if was.criterion != req.criterion:
            if signed:
                text = (f"{req_id} acceptance criterion changed after sign-off — "
                        f"scope drift against the signed baseline")
            else:
                text = f"{req_id} acceptance criterion changed"
            out.append(
                Event(when, commit, "req.criterion", req_id, text,
                      "scope" if signed else "progress")
            )

    for req_id in before:
        if req_id not in after:
            out.append(
                Event(when, commit, "req.removed", req_id,
                      f"{req_id} removed from requirements.md",
                      "scope" if signed else "attention")
            )
    return tuple(out)


def from_signoffs(previous, current, when: str, commit: str) -> tuple[Event, ...]:
    """A gate reaching sign-off. Names who approved and at which commit —
    both parsed today and shown nowhere."""
    if not readable(current):
        return ()
    if previous is not None and not readable(previous):
        return ()

    seen = {(s.gate, s.commit) for s in previous.signoffs} if previous is not None else set()
    out = []
    for signoff in current.signoffs:
        if (signoff.gate, signoff.commit) in seen:
            continue
        who = f" by {signoff.approved_by}" if signoff.approved_by else ""
        out.append(
            Event(when, commit, "gate.signed", signoff.gate,
                  f"{signoff.gate} signed off{who} — {signoff.artifact} at {signoff.commit}",
                  "milestone")
        )
    return tuple(out)


def epic_legible(parsed) -> bool:
    """Whether the epic field can be trusted — NOT whether the whole file is
    pristine.

    `readable()` asks the second question, and using it here was wrong.
    `from_engagement` reads exactly one field, and `engagement.md` records
    problems for conditions that say nothing about it: a title that reads
    `# Northwind Trading` instead of `# Engagement: Northwind Trading`, or an
    absent `## Progress reporting` block. Under the whole-file predicate a
    cosmetic h1 error swallowed `epic.assigned` entirely — the tracker key
    changed under the reader and the feed showed nothing.

    The epic's own failure modes need no predicate here, because they all
    arrive as an empty string: `parse_engagement` fills the field with
    `tracker.get("epic", "")`, so a missing `## Tracker` block and a Tracker
    block without an `epic:` field both land on `""`, which the callers'
    existing falsy check already rejects.

    This deliberately does NOT mirror `readable()`'s coupling to
    `serve._unparsed`. A commit whose `engagement.md` has an unrelated problem
    is still counted towards `feed.unreadable`, so this emits an event AND the
    footnote admits the file had problems. That asymmetry is the safe
    direction: the invariant exists to stop silent drops, and saying more is
    not the failure it guards against.
    """
    return bool(parsed.present) and parsed.engagement is not None


def from_engagement(previous, current, when: str, commit: str) -> tuple[Event, ...]:
    """The epic being created. Before this, /sync-tracker cannot run at all."""
    if not epic_legible(current):
        return ()
    if previous is None or not epic_legible(previous):
        return ()
    was, now = previous.engagement.epic, current.engagement.epic
    if was == now or not now or now == PENDING:
        return ()
    if was and was != PENDING:
        # A correction, not a creation. Every work item raised before this
        # commit was filed under the old epic, so the two trackers now split
        # the engagement's history between them. Silence here was the worst
        # of the three outcomes: whoever reconciles delivery against
        # the tracker finds items missing and has nothing telling them where
        # the boundary falls. Same kind as creation — the spec's kind budget
        # is fixed, and both answer "which epic does this engagement use".
        return (
            Event(when, commit, "epic.assigned", "epic",
                  f"Tracker epic changed — {was} → {now}", "attention"),
        )
    return (
        Event(when, commit, "epic.assigned", "epic",
              f"Tracker epic created — {now}", "milestone"),
    )
