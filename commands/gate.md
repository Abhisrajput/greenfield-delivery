---
description: Run a delivery gate end to end - produce the artifact, review it, prepare sign-off, record approval
argument-hint: discovery | requirements | design | build | handoff
---

# Gate

Run one gate of the delivery sequence. Use the `greenfield-delivery` skill for
the sequence, and the skill for this specific gate for the content standard.

## 1. Check the prerequisite

Read `docs/engagement/signoffs.md`. **The blocking predecessor must be recorded
as approved.**

| Running | Blocking predecessor |
|---|---|
| `discovery` | none — this is the first gate |
| `requirements` | none. Discovery is optional and may have been skipped; even when run, it gates the commercial shape, not the scope baseline |
| `design` | **Requirements** |
| `build` | **Design** |
| `handoff` | **Design** (build has no single sign-off; coverage is verified in `/handoff`) |

Only `design`, `build`, and `handoff` can be blocked. Do not block
`discovery` or `requirements` waiting for a sign-off that will never exist.

When the predecessor is missing, stop and say so in a sentence:

> Requirements aren't recorded as approved in `signoffs.md` yet. If the client
> approved out of band, tell me and I'll record it with the evidence — otherwise
> we should close gate 1 first.

Do not proceed on an assumption of approval. The sign-off record is what makes
the scope baseline defensible, and a gate run without it produces work with no
protection behind it.

## 2. Produce the artifact

| Gate | Artifact | Skill |
|---|---|---|
| discovery | `discovery.md` | `discovery` |
| requirements | `requirements.md` | `requirements-gate` |
| design | `design.md` + `CLAUDE.md` + `AGENTS.md` + `tasks.md` + `test-cases.md` | `architecture-design`, `business-test-cases` |
| build | working software; `tasks.md` worked down; `test-cases.md` run | `build-loop`, `build-standards`, `business-test-cases` |
| handoff | README, runbook, record | `handoff` |

## 3. Review before the client sees it

For requirements and design, run the `spec-reviewer` subagent. Fix what it
finds, or say explicitly why a finding is being accepted.

**Open questions must be empty** before an artifact goes for sign-off. An
artifact with open questions cannot serve as a baseline — the questions are
precisely where disputes will occur later.

## 4. Commit, then prepare the sign-off

Commit the artifact first, so the sign-off can reference a real SHA.

Draft the approval request. Keep it short, state what approval means, and make
the ask unambiguous.

**Send it in the channel the client already uses** — the Slack channel named in
`engagement.md`, an email, a meeting agenda, or a comment on the Confluence page
if that is where they live. A new channel for approvals is a channel they will
not check.

**Show it to the user before it goes. Never send it on their behalf.**

## 5. Record the approval

**"Yes, but change R3" is not approval.** It is a no with instructions: make
the change, commit it, and ask again against the new commit. Recording that
reply against the original SHA attaches their approval to a document they
explicitly asked you to change.

**Silence is not approval, and neither is "no objections".** If you are unsure
whether what came back is a yes, it is not one — ask again plainly.

Once the client approves, append to `signoffs.md`. **If the approval arrives
later — which is usual — use `/approve <gate>` rather than re-running this
command.** It records the row with the same checks and without redoing the gate.

| Gate | Artifact | Commit | Approved by | Date | Evidence |
|---|---|---|---|---|---|
| Requirements | requirements.md | a1b2c3d | J. Client | 2026-08-12 | Slack permalink |

**The commit SHA is the point.** "The client approved the requirements" is not
defensible; the SHA plus the permalink is.

Write the commit SHA into the `Commit` column, not into `Evidence`. If the
artifact has uncommitted changes at the moment of approval, stop and say so —
committing first is what makes the recorded SHA mean anything.

## 6. Tracker follow-through

| Gate | Tracker action |
|---|---|
| requirements | Create epic and one story per requirement, **then write the new epic ID back into the `## Tracker` block of `engagement.md`**, replacing `(pending)` |
| design | Break stories into work items from `tasks.md` |
| handoff | Close epic, export history into the record |

Run `/sync-tracker` for the mechanical part.
