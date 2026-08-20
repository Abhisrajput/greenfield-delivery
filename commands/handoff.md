---
description: Assemble the engagement delivery package and record for client acceptance
argument-hint: none
---

# Handoff

Close out the engagement. Use the `handoff` skill for the content standard.

## 1. Confirm there is a baseline to verify against

Coverage verification is the point of this gate, and it is meaningless without
an approved baseline. Stop and say so if:

- `requirements.md` is missing or has no requirements table
- `signoffs.md` has no approved Requirements row

Without those, you cannot state what was agreed, so you cannot state what was
delivered. Say:

> There's no approved `requirements.md` recorded in `signoffs.md`, so there's
> no baseline to verify delivery against. I can still assemble the README and
> runbook, but the delivery record would assert completeness nobody agreed a
> definition for. How do you want to handle it?

**Do not produce a delivery package that implies verified coverage when no
baseline exists.** That is the one output of this plugin a client may rely on
contractually.

## 2. Verify requirement coverage

Walk the requirements table. For each numbered requirement, determine whether
it is:

- **Met** — and demonstrable
- **Descoped** — with a recorded change request
- **Outstanding** — not done

Report the outstanding list plainly, in full, before proceeding.

**A requirement that is silently absent is the most expensive thing to discover
after acceptance.** Do not describe partial work as complete, and do not round
"mostly working" up to done.

## 3. Produce the package

| Artifact | Standard |
|---|---|
| `README.md` | A developer new to the project can run it without asking |
| Runbook | Whoever is on call can operate it — name the failure modes you know about |
| `CLAUDE.md` / `AGENTS.md` | Reflect the codebase **as delivered**, not as designed |
| Engagement record | Assembled from existing artifacts |

## 4. Update `CLAUDE.md` to reality

If the build diverged from the design and `CLAUDE.md` was not updated, update
it now. It is what the client's team and their agents will rely on after you
leave — a `CLAUDE.md` describing a system that was not built is worse than
none.

## 5. Assemble the record

| Component | Source |
|---|---|
| What was agreed | `requirements.md`, `design.md` |
| When, and by whom | `signoffs.md` with commit SHAs |
| What was built | git history |
| How it tracked | tracker export |

No service is needed. Git plus markdown plus a tracker export is a complete,
verifiable record.

## 6. Close the tracker

Close the epic. Export the work-item history into the record.

## 7. Name the retainer boundary

If the engagement rolls into support, say explicitly that this engagement is
closed and the next is separate scope. Handoff blurring into unbilled ongoing
work is the most common way a fixed-scope engagement ends up unprofitable after
it appeared to succeed.
