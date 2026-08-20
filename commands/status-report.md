---
description: Regenerate the client-facing status page for business stakeholders
argument-hint: none
---

# Status Report

Regenerate the narrative status page business stakeholders read. Use the
`progress-reporting` skill for the content standard.

## 1. Read the config

From `docs/engagement/engagement.md`, the `## Progress reporting` block gives
the target:

| `narrative` | Write to |
|---|---|
| `confluence` | The named page in the client's Confluence space |
| `ado-wiki` | The named markdown page in the client's ADO Wiki |
| `repo-markdown` | `docs/engagement/status.md` |

### Stop if the target is not fully specified

This command writes to a **client-visible surface**. Writing a status page into
the wrong client's Confluence space or wiki is a confidentiality incident, not
a bug — and it will look like it succeeded.

Stop and ask if any of these hold:

- `engagement.md` is missing, or has no `## Progress reporting` block
- `narrative:` is unset, `(pending)`, or not one of the three values above
- The target identifier for that surface is missing — `space:` and `page:` for
  Confluence, `wiki:` and `page:` for ADO Wiki

**Never fall back to a different surface** because the configured one looks
unavailable. A missing Confluence space means stop, not write to the repo
instead.

### Cross-check the client before writing

Confirm the target in `## Progress reporting` belongs to the same client as the
`## Tracker` block — the Confluence space or ADO wiki should correspond to the
same site or organization. If they disagree, stop and ask.

A firm running several engagements at once will eventually copy an
`engagement.md` between them. This check is what catches it before a page lands
in the wrong client's space.

## 2. Gather

| Source | For |
|---|---|
| `signoffs.md` | Which gates are approved, and when |
| `tasks.md` | What is in progress — canonical format in `greenfield-delivery` |
| Live tracker | Current item states, blockers |
| `requirements.md` | Requirement count, for coverage |

Query the tracker for live state rather than trusting `tasks.md` — the point of
regenerating is to be current.

## 3. Write

Follow the structure in `progress-reporting`. Four questions, in order:

1. Are we on track?
2. What has been agreed so far?
3. What is happening right now?
4. What needs a decision from the client?

**Lead with the answer.** First sentence is on track, at risk, or blocked.

**No internal shorthand** — no requirement numbers, no item IDs, no component
names the client has not heard. Write outcomes in the client's words.

**Report honestly.** If something slipped, say it slipped and why. A page that
reports green until the week before delivery destroys the trust the whole gate
process exists to build.

Include a link to the tracker dashboard for anyone who wants item-level detail.
If `dashboard:` is still `(pending)`, omit the link rather than inventing a URL,
and say it is missing — the dashboard is the half of progress
reporting that stays current without anyone running a command, so it is worth
setting up early.

## 4. Show before publishing

Show the page content to the user before writing it to a client-visible
surface. This is a client-facing artifact — it goes out under the firm's name,
and it should not be published without a human reading it first.

## 5. Confirm

Say where it was written and what changed since the last update.
