---
name: progress-reporting
description: Use when writing or updating a client-facing engagement status page for business stakeholders - in Confluence, ADO Wiki, or repository markdown.
---

# Progress Reporting

Produces the narrative status page business stakeholders read. The live
interactive picture is the tracker's own dashboard — this is the half that
needs writing.

## Where it goes

Read `engagement.md`:

```markdown
## Progress reporting
- narrative: confluence | ado-wiki | repo-markdown
```

| Value | Target |
|---|---|
| `confluence` | A page in the client's Confluence space |
| `ado-wiki` | A markdown page in the client's ADO Wiki |
| `repo-markdown` | `docs/engagement/status.md`, rendered by the git host |

The principle behind all three: **project into a system the client's business
users already log into.** No new URL, no new credential, no access control for
the firm to administer, and no service to keep running.

## Who this is for

A business stakeholder who was not in the standup, may not be technical, and is
deciding whether the engagement is on track.

**This is not a ticket dump.** Anyone who wants item-level detail has the
dashboard. This page answers four questions:

1. Are we on track?
2. What has been agreed so far?
3. What is happening right now?
4. What, if anything, needs a decision from them?

## Structure

```markdown
# <Client> — Delivery Status

_Updated <date>. Live board: <dashboard link>_

## Status
<One sentence. On track / at risk / blocked, and why.>

## Where we are
<Current gate, plain language. "Design approved; build started Monday.">

## Agreed so far
| Gate | Approved | Date |
|---|---|---|
| Requirements | ✅ | 2026-08-12 |
| Design | ✅ | 2026-08-15 |

## In progress
<Two or three lines on what is being built now. Outcomes, not tickets.>

## Needs a decision from you
<Anything blocked on the client. Empty is good — say "Nothing right now.">

## Next milestone
<What, and when.>
```

## Writing rules

**Lead with the answer.** The first sentence says on track, at risk, or
blocked. A stakeholder who reads only that line should not be misled.

**Report honestly.** If something slipped, say it slipped and why. A status
page that reports green until the week before delivery is worse than none — it
destroys the trust the gate process exists to build.

**No internal shorthand.** Not `R7`, not ticket IDs, not component names the
client has never heard. Write what changed in words they use.

**Keep "needs a decision" prominent and honest.** This is the section that
earns the page its readership. If the client is blocking something, it belongs
here, named, with the cost of the delay.

**Be brief.** If it is longer than a screen, it is a report nobody reads.

## Cadence

Regenerate with `/status-report` at each gate transition and on the agreed
reporting rhythm — usually weekly. Between updates, the dashboard carries the
live picture.

Always update it before a client meeting. Walking into a review with a stale
status page undoes the credibility the process is meant to produce.
