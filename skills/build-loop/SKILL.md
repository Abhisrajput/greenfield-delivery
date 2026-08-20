---
name: build-loop
description: Use when actually building - working a task from pick-up to merge with an agent, verifying the result, reviewing agent-written code and tests, and handling what to do when the build shows the specification was wrong. Gate 3 of the greenfield delivery sequence.
---

# The build loop

`build-standards` says what good looks like. This says what you **do**.

One task, start to finish. Gate 3 is where most of the engagement's hours go,
and where the failures that reach a client are made.

## The loop

1. **Check the task is ready.** The checklist is in `tracker-conventions`
   ("Ready to assign to an agent"). **An unready task is worse than no task** —
   the agent will produce something confident and plausible against its own
   reading of an ambiguous requirement, and you will spend longer discovering
   what it assumed than writing the thing yourself.
2. **One branch, one task**, with the work item ID in the name.
3. **Hand over the context, not the instruction.** The acceptance criterion
   **verbatim** from the approved `requirements.md`, the file boundaries it
   should stay inside, and `CLAUDE.md`. Do not paraphrase the criterion — a
   paraphrase is a second specification, and now two exist.
4. **Build.**
5. **Verify by driving it.** See below. This is the step that gets skipped.
6. **Review.** See below. Agent code fails differently from human code.
7. **Record**: work item status, `tasks.md`, and the test case result if one
   covers it.

Steps 5 and 6 are the work. Step 4 is the cheap part now, and treating it as
the expensive part is the central mistake of AI-assisted delivery.

## Split the criterion before you start

Acceptance criteria are written as sentences, and sentences hide conjunctions.
**Break the criterion into clauses and treat each as its own thing to build and
check.**

> A failed delivery records one reason from an agreed list, **and the
> dispatcher sees it within 1 minute**

That is two requirements. The first is about the driver, the second about
somebody else entirely, and a change can satisfy the first completely while
leaving the second untouched — which is exactly what happened when this was
built. The control worked, the reason was stored from a closed list, the tests
passed, and the failed job left the board so the dispatcher never saw it.

Watch for `and`, `then`, `so that`, and any second actor appearing halfway
through. A criterion mentioning two roles almost always contains two pieces of
work.

Doing this before you build costs a minute. Finding it at step 5 costs a
rebuild; finding it at acceptance costs the client's confidence.

## Verify by driving it

**Run the product the way a user reaches it.** Open the page. Call the
endpoint. Click the control. Log in as the other role.

A green test suite proves the code does what the tests say. It says nothing
about whether the feature is *reachable*, and nothing about whether the tests
assert anything.

That is not a theoretical risk. Every one of these shipped code that worked,
with tests that passed:

- A panel was fully implemented, tested, and **never called from the page
  renderer**. Six tasks of work, invisible, behind a green suite.
- A filter toggled a CSS class that **no stylesheet defined**. The control lit
  up; nothing was filtered.
- Domain logic for creating and assigning work was complete and covered — and
  **no HTTP route reached it**. The product could not do the thing its tests
  proved it did.

None of those was found by running tests or reading the diff. Each was found in
the first minute of using the thing.

**"I ran the tests" is not verification. "I used it" is.**

If the change is not drivable — a migration, a scheduled job, a retention
policy — say what you checked instead, and say what remains unverified. An
unverifiable change is not a failed one; describing it as verified is.

## Reviewing agent-written code

Human code tends to fail where the human was confused, and the confusion shows:
a hedge, a TODO, a variable named `temp2`. **Agent code fails where the
specification was ambiguous, and looks equally confident either way.** It does
not hedge, does not leave a TODO, and does not ask.

So review for different things.

### Read for what is missing, not for what is wrong

The code in front of you is usually correct *about itself*. Ask what is not
there:

- Is this reachable from the product, or only from its tests?
- Which acceptance criterion does each part serve? Anything serving none is
  scope the client did not ask for.
- What does it do when the input is absent, empty, or malformed? Those are
  three different cases and agents routinely collapse them into one.
- Did it change something it was not asked to change?

### Conventions are the easiest thing to imitate

An agent will match your file layout, naming, comment style and test structure
almost perfectly while doing the wrong thing. **Style conformance is evidence
of nothing.** A diff that looks like it belongs in the codebase has cleared the
lowest bar, not the highest one.

### Agent-written tests are the highest-risk artifact in the change

When the same agent writes the code and its tests, the tests can end up
asserting **what the code does** rather than what the requirement demands. They
pass by construction and will pass forever, including after the code breaks.

For every test in the change, ask: **would this fail if the code were wrong?**

Do not answer from reading. **Break the code and watch.** Invert the condition,
return a constant, delete the line the test is supposed to protect. A test that
still passes is decoration, and worse than nothing because it is counted.

Tests found this way in real work include: an ordering assertion comparing two
timestamps written in the same second, which passed with the sort deleted; an
assertion that a page did not say "0", which also passed when the page said
nothing at all; and a check that a command was documented, which was satisfied
by an unrelated sentence elsewhere in the file.

### Size is a review signal

A large diff for a small task means the agent decided something. Find out what.
The extra is usually either scope nobody asked for, or a workaround for an
obstacle worth knowing about.

## When the build shows the specification was wrong

This happens on real engagements and the methodology has to handle it, because
pretending it does not is how a signed baseline quietly stops describing the
system.

Three kinds, and they are handled differently:

| What you found | What it is | What to do |
|---|---|---|
| The requirement cannot be built as written | A specification defect | Stop. Take it back to the client — this is a change-order conversation. |
| Two readings of the criterion both look right | The criterion is not testable | Stop. It failed the requirements gate's own bar and needs one sentence from the client. |
| The requirement is right but something is missing around it | An ordinary gap | Raise a new work item against the same requirement. No client conversation needed. |

**A discovery during build is not permission to edit the requirement.**
`requirements.md` is signed against a commit; changing it silently makes the
approval on record describe something the client never saw. `/conform` will
catch it — `G3` — but catching it late is not the same as not doing it.

**Record the discovery either way.** An insight found during build and left in
someone's head is the most expensive thing in this whole process, because it
will be rediscovered at acceptance by the client.

If the design document needs to change — a deviation from the default stack, a
decision that turned out differently — that is the same rule. The design is
signed too. Amend it and have the client re-approve, which appends a second
sign-off row; the original stays as the history of what moved.

## Decisions the baseline left open

Not every decision during build changes the specification. Most do not: which
library, which shape, whether to reuse the client's existing service. The signed
baseline said nothing about them, so nothing is drifting — but the reasoning
still evaporates unless it is written down.

**Record those in `docs/engagement/decisions.md`** — the canonical format is in
`greenfield-delivery`. One row: what was decided, why, what was rejected, who
was in the room, when.

Worth doing when the answer to "why is it like this?" would otherwise be *"ask
whoever was on that call"*. In week eight that person is on another engagement,
and at handoff the client's team inherits a constraint with no reason attached
— which is how a sensible decision gets reverted six months later by someone
who assumed it was arbitrary.

Not everything is a decision. If it would not survive being asked about, it is
a preference; leave it out. A log that records every choice is one nobody reads.

**A decision that changes the approved design is not this.** That is an
amendment to `design.md`, and it needs the client to re-approve — see the table
above.

## Do not

- **Do not review by reading the diff alone.** It is the least reliable of the
  available checks and the most comfortable.
- **Do not accept "tests pass" as evidence.** Ask what the tests would catch.
- **Do not batch several tasks into one agent run.** The diff stops being
  reviewable, and a defect in one contaminates your confidence in the others.
- **Do not let an agent write the acceptance criteria.** They come from the
  approved requirements. A criterion written to match the code is not a check.
- **Do not mark a task done because the agent said it was done.** Done is the
  definition in `build-standards`, checked by you.
