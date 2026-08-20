---
name: greenfield-delivery
description: Use when working on a client greenfield engagement - starting one, moving through a delivery gate, writing requirements or design documents, syncing work to a tracker, or handing off. Defines the gate sequence and routes to the right skill for each step.
---

# Greenfield Delivery

The firm's methodology for greenfield client engagements. This skill is the
spine: it holds the gate sequence and routes to the skill that does the work.

## First: read the engagement config

Every engagement has `docs/engagement/engagement.md`. **Read it before doing
anything else.** It names the client, the tracker, the progress-reporting
surface, and the repository. Skills that act on a tracker will act on the wrong
project without it.

If it does not exist, this is not yet an engagement — run `/new-engagement`.

### `engagement.md` — canonical format

This is the contract every other skill reads. The block names and field names
below are load-bearing; do not rename them.

```markdown
# Engagement: <Client Name>

- **Started:** YYYY-MM-DD
- **Shape:** <e.g. Fixed-scope greenfield MVP, 6 weeks>
- **Primary contact:** <name, role>
- **Slack channel:** #<client>-delivery

## Tracker
- type: jira
- site: acme.atlassian.net
- project: ACME
- epic: ACME-142

## Progress reporting
- narrative: confluence
- space: ACME
- page: Delivery Status
- dashboard: <url>

## Repository
- url: https://github.com/<org>/<repo>
- default branch: main
```

For an Azure DevOps engagement, the two middle blocks instead read:

```markdown
## Tracker
- type: azure-devops
- org: https://dev.azure.com/acme
- project: ACME
- epic: 4821

## Progress reporting
- narrative: ado-wiki
- wiki: ACME.wiki
- page: /Delivery Status
- dashboard: <url>
```

`narrative` is one of `confluence`, `ado-wiki`, or `repo-markdown`.

#### Fields not known at setup

`epic:` and `dashboard:` cannot exist when `/new-engagement` runs — the epic is
created at gate 1, the dashboard later. Write them as `(pending)`:

```markdown
- epic: (pending)
- dashboard: (pending)
```

**Never invent a value for `epic:`.** `/sync-tracker` parents work items under
it, so a plausible-looking but wrong ID attaches client work to an unrelated
ticket in a live project — and it looks like it succeeded.

| Field | Filled by | When |
|---|---|---|
| `epic:` | `/gate requirements` | Immediately after creating the epic |
| `dashboard:` | You | Once the tracker dashboard exists |

Any skill that reads a `(pending)` field must **stop and say so** rather than
guess or proceed without it.

### How approval actually works

**Nothing here collects an approval.** No button, no workflow, no integration.
A person asks the client, the client answers in whatever channel they already
use, and a person writes down what happened. That is deliberate: an approval
the tooling generated would be an approval nobody gave.

The sequence, every gate:

1. **Commit the artifact.** Uncommitted changes at the moment of approval make
   the recorded SHA meaningless.
2. **Draft the ask** — short, naming what approval means and what is being
   approved. **Show it to the user; never send it yourself.**
3. **They send it.** Slack, email, a meeting agenda, a Jira or Confluence
   comment — the client's existing channel, not a new one.
4. **The client replies.**
5. **You record it** in `signoffs.md`: gate, artifact, **commit SHA**, who
   approved, the date, and a link to their reply.

### What counts as approval

**An unambiguous yes, from someone with the authority to give it, against a
named version.** All three parts matter:

| | Counts | Does not count |
|---|---|---|
| Clarity | "Approved", "yes, go ahead", 👍 on the request | "Looks good so far", "no objections", silence |
| Authority | The person named in `engagement.md` as primary contact, or someone they delegate to in writing | Anyone who happens to be in the channel |
| Version | A reply to the request naming *this* commit | A yes given before the last edit |

**Silence is never approval.** Neither is "no objections" — plenty of people
raise objections only once something ships. If you are unsure whether what you
received is a yes, it is not one; ask again plainly.

### Conditional approval is not approval

"Yes, but change R3" is extremely common, and it is a **no** with instructions.
Make the change, commit it, and ask again against the new commit. Recording the
first reply against the original SHA would attach their approval to a document
they explicitly asked you to change.

### If the approval was verbal

It happens — a meeting, a call, a corridor. Record it, and record it honestly:

| Gate | Artifact | Commit | Approved by | Date | Evidence |
|---|---|---|---|---|---|
| Requirements | requirements.md | a1b2c3d | R. Mensah, Ops Director | 2026-08-20 | Verbal, on the Thursday call — confirmation requested by email, not yet received |

Then **follow up in writing the same day** and update the row when the reply
lands. A verbal approval is real but not evidence, and the difference only
matters on the day it is disputed — which is the day you cannot fix it.

**Never write an evidence link that does not exist**, and never record an
approval you expect to receive.

### `signoffs.md` — canonical format

```markdown
# Sign-offs

| Gate | Artifact | Commit | Approved by | Date | Evidence |
|---|---|---|---|---|---|
| Requirements | requirements.md | a1b2c3d | Jane Doe, CTO | 2026-07-17 | <slack permalink> |
```

`Commit` is the SHA the artifact was approved at — the field that makes the
record defensible. It has its own column because it is the one fact that must
be machine-readable: `/dashboard` re-checks each approval against it.

Rows are appended by `/gate` on approval.

### `decisions.md` — canonical format

The working decisions made **between** gates. Optional on a solo engagement;
on a team it is the answer to "why is it like this?", which is the question
everyone asks in week eight and when someone joins mid-engagement.

```markdown
# Decisions — <Client>

| ID | Date | Decision | Why | Instead of | Decided by |
|---|---|---|---|---|---|
| D1 | 2026-08-20 | Reuse the existing auth service | Their team already operates it; a second one doubles the on-call surface | Building our own, which the design left open | R. Mensah and the delivery team, on the Thursday call |
```

| Column | Rule |
|---|---|
| `ID` | `D<n>`, unique. Never renumber — append, as with `R<n>` and `T<n>` |
| `Date` | When it was decided, not when it was written down |
| `Decision` | What was decided, in one line |
| `Why` | **Never blank.** The reason is the whole artifact |
| `Instead of` | What was rejected. `nothing considered` if there genuinely was no alternative |
| `Decided by` | Who was in the room — so the next person knows who to ask |

**This is not `design.md`.** They differ by *lifecycle*, not by subject:

| | `design.md` | `decisions.md` |
|---|---|---|
| When | At gate 2 | Any time |
| Signed | Yes, against a commit | No |
| Drift-checked | Yes — `/conform` `G3` | No |
| Changing it | A change-order conversation | Append a new row |

A decision that *changes the approved design* does not belong here — that is an
amendment to `design.md` and needs the client to re-approve it. This file is for
decisions the signed baseline left open.

**Append-only.** A decision that gets reversed gets a **new row** saying so,
referencing the one it replaces. Editing the original destroys the thing the
file exists for: that a choice was made, on a date, for a reason that seemed
good at the time.

**Do not record a decision without its `Why`.** A log of what was decided and
not why is a list of arbitrary-looking constraints, and the next team deletes
them.

### `tasks.md` — canonical format

Produced at gate 2. Read by `/sync-tracker`, `/status-report`, and `/dashboard`.

```markdown
# Tasks — <Client>

Produced at gate 2 from the approved `requirements.md`.

| ID | Task | Req | Owner | Status | Item |
|---|---|---|---|---|---|
| T1 | Add CSV export to the order list | R8 | Priya Nair | done | NWT-104 |
| T2 | Add scheduled export job | R9 | Sam Okoro | in-progress | NWT-105 |
| T3 | Add refund endpoint | R9 | Priya Nair | blocked | NWT-106 |
| T4 | Add order list pagination | R7 | (unassigned) | todo | (pending) |
```

| Column | Rule |
|---|---|
| `ID` | `T<n>`, unique. Never renumber — append, as with `R<n>` |
| `Task` | `<verb> <object>` per `tracker-conventions` |
| `Req` | Exactly one `R<n>` or `N<n>`. Never blank. `none` if deliberately unlinked |
| `Owner` | Who is doing it. **Written by `/sync-tracker` from the tracker, not by hand.** `(unassigned)` if nobody is — never blank |
| `Status` | Exactly one of `todo`, `in-progress`, `blocked`, `done`, `dropped` |
| `Item` | Tracker work item ID, or `(pending)` before `/sync-tracker` creates it |

**The header row is load-bearing.** Readers match it exactly and do not fall
back to column position. A reordered header must stop the reader, not produce
a plausible misreading.

**`Req` is never blank.** A blank cell conflates "deliberately unlinked" with
"not filled in". Write `none` for the first; a blank cell is a malformed row.

**`Owner` is derived, not authored.** The tracker owns assignment — the team
already changes it there, and a second copy maintained by hand goes stale within
a week and becomes something everyone learns to disbelieve. `/sync-tracker`
pulls it across with the status. On a solo engagement it will read your name or
`(unassigned)` throughout, and costs nothing.

**`dropped` rather than deleting the row.** Deleting silently shrinks the
denominator, so completion jumps with nothing recording that scope was cut. On
a fixed-scope engagement that is a change-order conversation, so it stays
visible.

## The gate sequence

| Gate | Artifact | Client action | Skill |
|---|---|---|---|
| 0. Discovery *(optional)* | `discovery.md` | Agrees problem and commercial shape | `discovery` |
| 1. Requirements | `requirements.md` | 👍 — **scope baseline** | `requirements-gate` |
| 2. Design | `design.md`, `CLAUDE.md`, `AGENTS.md`, `tasks.md`, `test-cases.md` | 👍 — architecture agreed | `architecture-design` |
| 3. Build | working software; `tasks.md` worked down | demos, visible progress | `build-loop`, `build-standards` |
| 4. Handoff | README, runbook, delivery record | acceptance | `handoff` |

`tasks.md` is **produced at gate 2** — breaking the approved requirements into
a task list is a design output. Gate 3 works that list down; `/sync-tracker`
translates it into tracker work items.

`test-cases.md` is produced at gate 2 for the same reason and from the same
source: it is written against requirements the client has already **approved**,
so the cases are pinned to the signed baseline rather than to a document still
moving. Gate 3 runs them as the work lands, and gate 4 uses their results as
acceptance evidence. See `business-test-cases`.

## The non-negotiable rule

**Gates are sequential, and each requires recorded client approval before the
next begins.**

Approval is recorded in `docs/engagement/signoffs.md` as a row containing the
artifact, the **commit SHA** it was approved at, who approved, the date, and a
link to the evidence (usually a Slack permalink).

The commit SHA is what makes the record worth having. "The client approved the
requirements" is not defensible; "the client approved `requirements.md` at
`a1b2c3d` on 2026-08-12, per this Slack message" is.

### When asked to skip a gate

Say so plainly, in a sentence, and ask for the prior approval to be recorded
first. Do not quietly proceed. The gate sequence is what converts "the AI built
the wrong thing" from the firm's problem into a signed-off change order — a
skipped gate removes that protection precisely when it is most needed.

If the client has genuinely approved out of band, record the approval in
`signoffs.md` with the evidence, then continue.

## Scope discipline

Anything not in the approved `requirements.md` is a change request. When work
in flight drifts outside it:

1. Name the drift explicitly.
2. Say whether it is a change request or a clarification within scope.
3. If it is a change request, it goes back through gate 1 — a new numbered
   requirement, re-approved, re-recorded.

Do not absorb scope silently. Absorbed scope is unbilled work and it destroys
the margin on a fixed-scope engagement.

## Routing

| Working on | Use |
|---|---|
| Scoping conversation, estimate | `discovery` |
| Acceptance criteria | `requirements-gate` |
| Architecture, stack, `CLAUDE.md` | `architecture-design` |
| Working a task with an agent, and reviewing what it produced | `build-loop` |
| Code standards, stack, definition of done | `build-standards` |
| Test cases a business user can run and accept | `business-test-cases` |
| Work item titles, criteria, estimates | `tracker-conventions` |
| Jira / Confluence specifics | `tracker-jira` |
| Azure DevOps / Wiki specifics | `tracker-azure-devops` |
| Client-facing status page | `progress-reporting` |
| Delivery package | `handoff` |

## Commands

| Command | Does |
|---|---|
| `/new-engagement` | Scaffold `docs/engagement/`, write `engagement.md` |
| `/gate <name>` | Run a gate end to end, including the sign-off record |
| `/sync-tracker` | Push `tasks.md` into the tracker; pull status back |
| `/status-report` | Regenerate the client-facing status page |
| `/handoff` | Assemble the delivery package |
