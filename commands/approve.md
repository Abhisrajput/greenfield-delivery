---
description: Draft a gate approval request, or record an approval the client has given
argument-hint: <gate> [request]
---

# Approve

Two jobs, because approval arrives on the client's schedule, not yours:

| | |
|---|---|
| `/approve <gate> request` | Draft the message asking for approval |
| `/approve <gate>` | Record an approval that has **already** arrived |

You run a gate on Monday and the client replies on Thursday. Re-running `/gate`
to record one row would redo the whole thing.

**This command writes the record every other check trusts.** A row here is what
`/conform` verifies, what `/dashboard` shows as a green tick, and what gets
pointed at in a dispute. It is the one place in this plugin where inventing a
value would be indistinguishable from the truth.

## 1. Check the inputs

**If no gate was given, stop and ask.** Do not infer it from the most recently
changed file.

Read `docs/engagement/signoffs.md` and `docs/engagement/engagement.md`.
**If either is missing, stop** — this is not an engagement, or not one that has
reached a gate.

The gate must be one of `discovery`, `requirements`, `design`, `build`,
`handoff`. **Anything else, stop and say so.**

---

# `/approve <gate> request` — draft the ask

## 2. Confirm there is something to approve

The gate's artifact must exist and be **committed with no uncommitted changes**.

**If it has uncommitted changes, stop and say so.** Committing first is what
makes the SHA mean anything — an approval recorded against a commit that does
not match what they read is worse than no record.

Report the SHA they will be approving.

## 3. Draft it

Short, and unambiguous about what approval means. Follow the gate's own skill
for the wording — `requirements-gate` has the requirements version.

Name what is being approved, what changes as a result, and what happens to
anything not in it.

**Send it where the client already is** — the channel in `engagement.md`, an
email, a meeting agenda, a comment on the Confluence page. A new channel for
approvals is one they will not check.

**Show it to the user. Never send it yourself.** Approval is a conversation
between two people, and a request that arrived from an automation invites a
reply that was never really considered.

---

# `/approve <gate>` — record what arrived

## 4. Establish that it is actually an approval

Ask for the reply, in the client's words. Then check three things, and
**stop if any of them fails**:

| | Required | Not this |
|---|---|---|
| Clarity | An unambiguous yes | "Looks good so far", "no objections", silence |
| Authority | The contact in `engagement.md`, or someone they delegated to in writing | Anyone who happened to be in the channel |
| Version | Given against the current commit | A yes from before the last edit |

**"Yes, but change X" is not an approval.** It is a no with instructions. Say
so, make the change, and ask again against the new commit.

**If you are unsure whether the reply is a yes, it is not one.** Say that
plainly rather than recording a maybe.

## 5. Ask for what you cannot know

Never fill these in yourself:

- **Who approved** — their name and role, as it should appear in the record
- **When** — the date they approved, not today's date if those differ
- **Evidence** — a permalink to their reply

**If there is no link because the approval was verbal**, record it as verbal and
say written confirmation was requested:

> `Verbal, on the Thursday call — confirmation requested by email, not yet received`

Then tell the user to follow up the same day, and to run `/approve` again to
update the row when it lands. A verbal approval is real, but it is not evidence,
and the difference only matters on the day it is disputed.

**Never write an evidence link you have not been given.**

## 6. Check the order

`design` requires `requirements` approved; `build` and `handoff` require
`design`. Discovery and requirements have no blocking predecessor.

**If the predecessor is not recorded as approved, stop and say so.** The client
may well have approved out of band — offer to record that first, with its own
evidence. Do not record them together as though both were given now.

## 7. Append the row

Append to `signoffs.md` — never edit an existing row:

| Gate | Artifact | Commit | Approved by | Date | Evidence |
|---|---|---|---|---|---|
| Requirements | requirements.md | a1b2c3d | R. Mensah, Ops Director | 2026-08-20 | https://… |

The `Commit` column takes the SHA, not the evidence link.

**Amending an earlier approval appends a second row for the same gate**, at the
new commit. The original stays — it is the record that scope moved, and when.
Editing it destroys exactly that.

## 8. Confirm, then check

Say which gate is now approved, at which commit, and what it unblocks.

Run `/conform`. The gate that was failing `G3` should now pass, because the
recorded approval covers the current file. **If it still fails, say so rather
than adjusting the record** — a check that goes green because someone edited the
evidence is not a check.
