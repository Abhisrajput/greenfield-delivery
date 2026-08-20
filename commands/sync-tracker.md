---
description: Sync tasks.md into the engagement tracker and pull status back
argument-hint: Optional - push, pull, or both (default both)
---

# Sync Tracker

Translate the agreed task list into the client's tracker and reflect status
back. This is a translation step, not a thinking step — `tasks.md` already
exists from gate 2.

## 1. Read the config

From `docs/engagement/engagement.md`, read the `## Tracker` block: type, site
or org, project, epic.

**Scope every call to that project.** MCP servers reach every site or
organization the authenticated account can access, so an unscoped call can act against a
different client's project. If the block is missing, stop and ask — do not
infer the target.

**If `epic:` is `(pending)`, stop.** Work items are parented under it, so
guessing attaches client work to an unrelated ticket in a live project — and
the call succeeds, so nothing surfaces the mistake. Say:

> `engagement.md` still has `epic: (pending)`. The epic is created by
> `/gate requirements` — run that first, or tell me the epic ID and I'll record
> it.

Then load the matching skill: `tracker-jira` or `tracker-azure-devops`.

`tasks.md` has a canonical format — see the `greenfield-delivery` skill. Read it
before writing anything back. The `Status` column takes exactly one of `todo`,
`in-progress`, `blocked`, `done`, `dropped`, and the `Item` column takes the
work item ID or `(pending)`.

**Do not invent a status value.** Anything outside the five makes the row
unreadable to `/status-report` and `/dashboard`, which report it as malformed
rather than guessing.

### Map by status *category*, not by status name

Trackers let every project invent its own status names, so matching on the name
does not survive contact with a real project. Jira's default software workflow
already includes **In Review**, which is none of the five — matching by name
would stop and ask on the most common workflow there is, every time.

Every Jira status belongs to exactly one of three **status categories**, and
that is the stable thing to read:

| Status category | `tasks.md` |
|---|---|
| `new` | `todo` |
| `indeterminate` (Jira shows this as "In Progress") | `in-progress` |
| `done` | `done` |

So "In Review", "In QA", "Awaiting deploy" and any other invented in-flight
status all arrive as `in-progress` without anyone being asked. Azure DevOps has
the same idea: its states roll up to *Proposed*, *InProgress*, *Resolved*,
*Completed*.

**If a state has no category, or the category is unrecognised, stop and ask.**
That is a mapping decision, not something to guess.

### Pull the assignee across with the status

`tasks.md` has an `Owner` column, and **`/sync-tracker` is the only thing that
writes it.** Take the tracker's assignee, write the person's display name — not
an account ID, because the column is read by people — and write
`(unassigned)` when the tracker has nobody on it.

Never blank. A blank cell conflates "nobody is on this" with "nobody filled it
in", and on a team those need different conversations.

**Do not write an owner the tracker did not give you.** Not the person running
the command, not whoever last touched the file. If the item has no assignee,
the honest answer is `(unassigned)` — the same rule as `(pending)` for an item
that does not exist yet.

### `blocked` and `dropped` are local, and a pull must never erase them

Neither has a tracker equivalent. A blocked task is usually still sitting in an
in-flight status, and a dropped one is often still open — the tracker has no way
to say either.

So **never overwrite a local `blocked` or `dropped` with a pulled value.** The
category would say `in-progress`, and writing it silently erases the fact that
the work is stuck or that scope was cut — the two states most worth reporting.
Pull into rows that are `todo`, `in-progress` or `done`; for the others, report
what the tracker says and leave the row alone.

Blocked in the tracker — a Jira flag, or a blocked-by link — is a signal to
**report**, not to absorb: it belongs in the drift report below.

## 2. Push

For each entry in `tasks.md` with no corresponding work item:

- Title as `<verb> <object>` per `tracker-conventions`
- Body containing the requirement number, context, acceptance criteria, and
  out-of-scope notes
- **Acceptance criteria copied verbatim from `requirements.md`** — never
  paraphrased. The tracker and the signed baseline must agree word for word.
- Parented to the correct epic or story

Record the created item ID back into `tasks.md`'s `Item` column so the mapping
survives. Preserve the table's column order and header exactly — readers match
the header verbatim and stop if it changes.

### Two people may sync at once

On a team this is an ordinary Tuesday, and the create step is where it hurts:
both runs read `tasks.md`, both see `(pending)`, and both create a work item for
the same task. The result is a duplicate nobody notices until the board looks
wrong.

**Search before creating.** For each task with `(pending)`, search the epic for
an existing item referencing that task ID before creating one. If it is already
there, write its key back rather than creating a second. Being idempotent by
*search* is what makes a concurrent run harmless; assuming `(pending)` means
"does not exist" is what makes it destructive.

**Re-read `tasks.md` immediately before writing it.** A sync takes long enough
for someone else to have committed a change, and writing a file you read two
minutes ago silently reverts their work.

If a duplicate does appear, **report it — do not delete it.** A work item may
already carry someone's comments or time, and the tracker is the client's.

## 3. Pull

For each work item, reflect current status into `tasks.md`. Report anything
that has been:

- Closed but is not checked off locally
- Blocked
- Moved out of the epic — this is usually scope drift and should be named

## 4. Report drift, do not absorb it

Two things to surface explicitly rather than silently reconcile:

- **Work items with no requirement link** — scope creep, visible early
- **Requirements with no work items** — unplanned work

Both are conversations, not cleanup. Absorbing them silently is how a
fixed-scope engagement loses margin.

## 5. Summarise

Say what was created, what was updated, and what drifted. Be specific about
counts and item IDs; a sync that reports "done" tells the reader nothing
about whether it did the right thing.
