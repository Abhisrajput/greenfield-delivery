---
name: business-test-cases
description: Use when writing or reviewing business test cases for an engagement - turning approved requirements into scenarios a business user can execute and accept, tracking their results, and taking them into handoff acceptance.
---

# Business test cases

The bridge between "the client approved these requirements" and "the client
accepts this software". Acceptance criteria say what *good* means; test cases
are what someone actually **does** to find out, written so a business user can
do it without the delivery team in the room.

Produced from **approved** requirements — after the Requirements gate is
signed, so the cases are written against the baseline rather than a moving
target. Run during Build as work lands, and again at Handoff, where their
results are the acceptance evidence.

## The distinction that matters

A developer test proves the system behaves. A business test proves the
**business outcome** happened, in the client's own vocabulary.

| Not this | This |
|---|---|
| "Assert POST /orders returns 201" | "Submit an order for account NW-4471 and note the confirmation number" |
| "Verify the record is updated" | "The order shows **Approved**, and Dana receives the confirmation email" |
| "Check rejection handling works" | "Reject the order with reason *Credit limit exceeded* — the customer sees that reason within a minute" |

If executing the case requires reading a log, querying a database, or knowing
an endpoint, it is not a business test case. Rewrite it or move it to the
build's own test suite.

## `test-cases.md` — canonical format

Written to `docs/engagement/test-cases.md`.

```markdown
# Test cases — <Client>

Written from `requirements.md` as approved at <commit>.

| ID | Req | Mode | Scenario | Given | When | Then | Result |
|---|---|---|---|---|---|---|---|
| TC1 | R1 | automated | Submit a valid wholesale order | Account NW-4471 is active | The customer submits a 3-line order | A confirmation number appears within 5 seconds | pass |
| TC2 | R1 | automated | Submit against a closed account | Account NW-9902 is closed | The customer submits any order | The order is refused, naming the closed account | not run |
| TC3 | R5 | manual | Reject an order with a reason | An order is awaiting review | The reviewer rejects it as "Credit limit exceeded" | The customer sees that reason within 1 minute | fail |
```

| Column | Rule |
|---|---|
| `ID` | `TC<n>`, unique. Never renumber — append, as with `R<n>` and `T<n>` |
| `Req` | Exactly one `R<n>` or `N<n>`. **Never blank and never `none`** |
| `Mode` | Exactly one of `manual`, `automated`. Stated, never inferred — see `qe` |
| `Scenario` | What is being proved, in one line, in the client's language |
| `Given` | The precondition, including the **named** test data |
| `When` | The single action the business user takes |
| `Then` | What they observe — visible, and specific enough to be wrong |
| `Result` | Exactly one of `not run`, `pass`, `fail`, `blocked` |

**The header row is load-bearing.** Readers match it exactly and do not fall
back on column position, as with `tasks.md`.

### `Req` is never `none`

`tasks.md` permits `none` for deliberately unlinked work. Test cases do not. A
test case that traces to no requirement is testing something the client never
asked for and never approved — which is either a missing requirement or work
that should not be happening. Raise it; do not file it under `none`.

### `Result` defaults to `not run`, never blank

A blank result conflates "we have not tried this yet" with "this passed".
At handoff those are opposite claims. `not run` is the honest starting value
for every case, and it is what a case stays until someone actually runs it.

**Never mark a case `pass` because the implementation looks right.** A pass is
a record that a person executed the steps and observed the result. If nobody
ran it, it has not passed, however obviously correct the code is.

`blocked` is for a case that cannot be run yet — the environment is down, the
test account does not exist, an upstream case failed. It is not a soft `fail`,
and it must name what is blocking it.

## Writing them

**One case per thing that can independently go wrong**, not one per
requirement. R1 above needs at least the happy path and the closed account;
a single case covering both proves neither when it fails.

**Cover the refusal paths.** Most business risk lives in what happens when
something is rejected, expired, over a limit, or submitted twice. A suite that
only walks the happy path accepts a system nobody has tried to misuse.

**Name the test data, and agree it.** "A valid account" is not executable;
`NW-4471` is. Where the data does not exist yet, say so in `Given` and raise
it — do not invent an account number and do not quietly assume the client will
create one.

**Never invent an expected result the client did not agree to.** A `Then` you
wrote yourself reads exactly like one they approved, and only one of those can
be held up at acceptance. Where the requirement is silent about what should
happen, that is a gap in `requirements.md` — take it back to the requirements
gate rather than deciding it here.

**Do not restate the acceptance criterion as the test.** "The thing is done
within 5 seconds" is the criterion; the case is what you do to find out whether
it was. If `Then` is a copy of the criterion, no one can execute it.

### Mode is a delivery decision, not a business one

`automated` means a machine observes the same thing the business user would.
`manual` means a person runs it, and that is a legitimate permanent answer —
some outcomes are judgments, and some cannot honestly be proved inside the
engagement at all.

Write the case first and decide the mode second. A case written to be easy to
automate is usually a case that stopped describing the business outcome. The
`qe` skill covers generating an executable suite from these.

## Coverage

Every in-scope requirement — functional and non-functional — needs at least one
case. Out-of-scope items get none; they are the list of things deliberately not
built.

A requirement with no test case cannot be accepted, only assumed. Report those
explicitly rather than letting the suite look complete:

> R7 and N2 have no test cases. R7 is a reporting requirement nobody has
> described how to check; N2 is the seven-year retention rule, which cannot be
> proved in a six-week engagement. Both need a decision before handoff.

Non-functional requirements are where this gets skipped. Availability and
retention are hard to test inside an engagement, and the honest move is to say
what will be checked and what will only be designed for — not to write a case
that quietly proves nothing.

## Running them

During Build, run cases as the work they cover lands, and record the result
then. A suite executed for the first time the week before handoff finds
problems at the worst possible moment, which is the entire argument for
running them early.

Record a result as it happens. Do not batch-update at the end from memory.

## When a case fails

A `fail` is a conversation, not a ticket to file quietly.

Establish which of these it is before doing anything:

1. **The software is wrong** — a defect. Raise it in the tracker per
   `tracker-conventions`, link the requirement, fix it, re-run the case.
2. **The test case is wrong** — it tests something the requirement never said.
   Fix the case, and say you changed it.
3. **The requirement is wrong** — the client wants something different from
   what they approved. **This is scope drift against a signed baseline.**
   Do not edit `requirements.md` to match the new expectation and move on:
   that rewrites what was agreed. Take it through the change-order
   conversation, and let `/dashboard` and `/conform` show the drift.

The third is the expensive one and the easiest to mistake for the first.

## At handoff

The `handoff` skill takes the results as acceptance evidence. Bring:

- every case with a result that is not `not run`
- the list of requirements with no case, and why
- every `fail` and `blocked` case with what was decided about it

**Do not present a suite as complete when cases were never run.** Say how many
were run, how many passed, and what was not checked — the same three-way
distinction `/conform` makes. A suite reported as passing when a third of it
was never executed is worse than no suite, because it is believed.
