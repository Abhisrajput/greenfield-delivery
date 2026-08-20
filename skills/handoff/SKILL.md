---
name: handoff
description: Use when closing out a client engagement - assembling the delivery package, writing the runbook, or producing the engagement record for acceptance. Gate 4 of the greenfield delivery sequence.
---

# Handoff

Gate 4. Produces the delivery package and the engagement record.

## What the client receives

| Artifact | Purpose |
|---|---|
| `README.md` | How to run, build, test, and deploy the project |
| Runbook | How to operate it once running |
| `CLAUDE.md` / `AGENTS.md` | How their team's agents should work in this codebase |
| Engagement record | What was agreed, when, and by whom |

## README

Written for a developer on the client's team who has never seen the project.
The test: could they get it running locally without asking you anything?

Cover prerequisites with versions, setup, how to run tests, how to run the app,
how to deploy, and where configuration and secrets come from. Do not document
architecture here — that is `design.md` and `CLAUDE.md`.

## Runbook

Written for whoever is on call, who may not be a developer.

- How to tell whether it is healthy
- The failure modes you know about, and what each looks like
- What to do about each
- What to check before escalating
- Who to escalate to, and what to include

A runbook that only says "check the logs" is not a runbook. Name the specific
things that break in *this* system, which you know and they do not.

## Engagement record

The delivery record is the firm's protection and the client's evidence. It is
assembled from artifacts that already exist:

| Component | Source |
|---|---|
| What was agreed | `requirements.md`, `design.md` |
| Why it is like this | `decisions.md` — the working decisions the baseline left open |
| When and by whom | `signoffs.md`, with commit SHAs |
| What was built | git history |
| How it tracked | tracker work-item history, exported |

No service is needed to produce this. Git plus markdown plus a tracker export
is a complete, verifiable record.

### Verify before delivering

Walk the requirements table and confirm each numbered requirement is either
met, explicitly descoped with a recorded change request, or listed as
outstanding. **A requirement that is silently absent is the single most
expensive thing to discover after acceptance.**

State outcomes plainly. If something is not done, say it is not done and why —
do not describe partial work as complete.

The evidence for "met" is `test-cases.md`, not an assertion. Bring the results:
how many cases ran, how many passed, every `fail` and `blocked` case with what
was decided, and the requirements that have **no** case at all. See
`business-test-cases`.

**A requirement whose cases were never run is not met, it is unverified**, and
those are different words in an acceptance conversation. Reporting a suite as
passing when part of it never ran is worse than having no suite, because it is
believed.

## Transferring agent configuration

Confirm `CLAUDE.md` reflects the codebase as delivered, not as designed. If the
build diverged and the file was not updated, update it now — it is what the
client's team and their agents will rely on.

Point out that `AGENTS.md` exists and what it is for. Most clients do not know
the convention, and it is the artifact that keeps their standard from decaying
after you leave.

## Retainer boundary

If the engagement rolls into a support arrangement, that is a separate scope
with its own artifacts. Do not let handoff blur into unbilled ongoing work —
close this engagement formally first, then start the next one.
