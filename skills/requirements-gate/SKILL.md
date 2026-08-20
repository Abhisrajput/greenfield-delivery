---
name: requirements-gate
description: Use when writing or reviewing engagement requirements and acceptance criteria, or preparing the client sign-off that establishes the scope baseline. Gate 1 of the greenfield delivery sequence.
---

# Requirements Gate

Gate 1. Produces `docs/engagement/requirements.md` — **the scope baseline**.
Everything after this gate is measured against this document.

## Why this gate carries the commercial weight

Approved requirements are what convert "the AI built the wrong thing" from the
firm's problem into a signed-off change order. A vague requirements document
does not just cause rework; it removes the firm's protection at the exact
moment it is needed.

Write it accordingly.

## Where requirements come from — and when the gate happens

**Gathering is incremental. Approval is a moment.** Those are different things,
and conflating them is what makes people think this is one-shot.

Requirements arrive over several conversations, from several sources, in
whatever shape the client had them:

| Input | What to do |
|---|---|
| A conversation or call | Extract candidates, confirm them, add rows |
| A transcript or meeting notes | See below — extraction, not conversion |
| A document the client already wrote | `/import-artifact requirements <path>` |
| A Confluence page | `/import-artifact requirements <page URL or ID>` — records the page version |
| A Slack thread, an email, a spreadsheet | Same as a transcript: extract, mark, confirm |
| Something remembered mid-build | It is a change to a signed baseline — see below |

`requirements.md` accumulates across all of that. Add rows as they firm up. It
is a working document until the moment it is not.

**The gate is the moment you stop gathering and ask for approval.** Nothing
about it says the requirements arrived all at once — only that from here, this
version is the baseline, recorded against the commit the client approved.

### After the gate: amend, never edit

A requirement discovered after sign-off does not get quietly added. The signed
version is what the client agreed, and `/conform` will notice it changed —
`G3`, correctly.

Amending is a real, supported path and it takes about a minute:

1. Add or change the requirement in `requirements.md`.
2. Commit it.
3. Take the change to the client — this is the change-order conversation, which
   on fixed-scope work is the entire point.
4. On approval, **append a new row to `signoffs.md`** at the new commit. The
   original row stays. `/conform` then reads the current approval and goes
   green, and the record shows the baseline moved, when, and who agreed.

**Do not edit the original sign-off row.** That erases the fact that scope
changed, which is the one thing the record exists to preserve.

### Extracting requirements from a transcript

Transcripts are the most common real input and the most dangerous, because a
conversation contains decisions, half-decisions, thinking aloud, and things
somebody said to be polite. An agent reading one will produce confident,
well-formatted requirements from all four.

**Everything extracted is a candidate until the client confirms it.** Put
candidates under `## Open questions` with the quote that produced them, not
under `## Functional` with an invented acceptance criterion:

```markdown
## Open questions

| # | Question | Blocking |
|---|---|---|
| Q1 | "we'd probably want them to get an email too" — is customer notification in scope, and on which events? | Yes |
```

Never write an acceptance criterion the client did not say. If the transcript
does not contain a testable condition — and it usually does not, because people
do not speak in acceptance criteria — the criterion is unknown, and unknown
goes in the question, not in the table.

**A requirement nobody said out loud is the most expensive thing you can add**,
because it looks exactly like one they asked for and it will be built.

## Acceptance criteria standard

Every requirement is **numbered**, **individually testable**, and **atomic**.

### Numbered

`R1`, `R2`, `R3`. Numbers are referenced in work items, in change requests, and
in the handoff record. Never renumber — append, and mark superseded items as
superseded.

### Individually testable

Someone who was not in the conversation must be able to determine pass or fail
without asking you.

**Weak:** "The dashboard should be fast and easy to use."
**Strong:** "R7 — The order list renders within 2 seconds for an account with
10,000 orders."

### Atomic

One requirement, one criterion. Compound requirements cannot be partially
accepted, so a single unmet half blocks the whole item.

**Weak:** "R4 — Users can export orders as CSV and Excel and schedule exports."
**Strong:** `R4` CSV export, `R5` Excel export, `R6` scheduled exports.

Splitting also lets scope be cut cleanly under deadline pressure: dropping `R6`
is a conversation, dropping "half of R4" is not.

## Non-goals are requirements too

Include an explicit **Out of scope** section. It is the cheapest possible
protection, and it is where most fixed-scope engagements lose margin.

If it was discussed and excluded, write it down. "We never said we'd do that"
is much weaker than "R-out-3: no mobile application in this release."

## Output shape

```markdown
# Requirements — <Client>

Baseline for the engagement. Anything not listed here is a change request.

## Functional

| # | Requirement | Acceptance criterion |
|---|---|---|
| R1 | ... | ... |
| R2 | ... | ... |

## Non-functional

| # | Requirement | Acceptance criterion |
|---|---|---|
| N1 | ... | ... |

## Out of scope

| # | Excluded | Note |
|---|---|---|
| X1 | ... | ... |

## Open questions
<anything blocking; must be empty before sign-off>
```

## Before it goes to the client

Run the `spec-reviewer` subagent. It checks for untestable criteria, compound
requirements, missing non-goals, and unstated assumptions.

**Open questions must be empty.** A requirements document with open questions
cannot be a scope baseline — the questions are exactly where scope disputes
will later occur.

## The sign-off

Prepare the Slack post alongside the document. Keep it short and make the ask
unambiguous:

> Requirements for <project> are ready for review: <link>
>
> This is the scope baseline — once approved, anything not in it is a change
> request. <N> requirements, <M> explicitly out of scope.
>
> Please reply 👍 to approve, or comment on anything that needs to change.

On approval, record the row in `signoffs.md` with the **commit SHA** of the
approved document, and create the tracker epic and stories.
