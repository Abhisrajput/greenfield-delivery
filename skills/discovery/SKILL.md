---
name: discovery
description: Use when scoping a new client engagement before requirements - running a discovery conversation, writing a problem statement, or producing an estimate range. Gate 0 of the greenfield delivery sequence.
---

# Discovery

Gate 0. Produces `docs/engagement/discovery.md` and the commercial shape of the
engagement. This gate is optional — delete this skill if scoping happens
entirely in the sales process.

## What discovery is for

Establishing three things well enough to price the work:

1. **The problem**, stated in the client's terms, not in solution terms.
2. **The constraints** — deadline, budget, existing systems, compliance, who
   has to approve.
3. **The rough shape** — what a first release contains, and explicitly what it
   does not.

Discovery is not design. Resist producing an architecture here; the goal is a
defensible estimate range, not a solution.

## The problem statement

Write it as the client would recognise it. A good problem statement:

- Names who is affected and what it currently costs them
- Is falsifiable — you could tell whether it had been solved
- Contains no technology choices

**Weak:** "They need a React dashboard with a Node backend."
**Strong:** "Ops leads spend roughly a day a week reconciling order data by
hand across three systems, and errors surface only after customers complain."

## Capture the tracker

**Record which tracker the client uses.** This is not administrative detail —
it changes the estimate.

Atlassian clients can have well-specified work items assigned to Claude for
unattended draft pull requests. Azure DevOps clients cannot; there is no
Anthropic-native agent for it, so the build phase is entirely attended.

**An Azure DevOps engagement therefore consumes more hands-on time than an
equivalent Atlassian one.** Reflect that in the estimate, or the margin
disappears quietly. If the client has no strong preference, this is a reason to
recommend Atlassian.

## The estimate

Give a range, not a number, and state what would move it to each end.

State assumptions explicitly and numbered — they become the basis for change
requests later. An assumption that turns out false is a scope conversation, and
that conversation is much easier when the assumption was written down.

## Output: `discovery.md`

```markdown
# Discovery — <Client>

## Problem
<the problem statement>

## Who is affected
<roles, volumes, current cost>

## Constraints
- Deadline:
- Budget shape:
- Existing systems:
- Compliance / data handling:
- Approvers:

## First release — in scope
<bulleted, coarse>

## First release — explicitly out of scope
<bulleted; this is as important as the in-scope list>

## Tracker
<jira | azure-devops>, and the margin implication if ADO

## Assumptions
1. ...
2. ...

## Estimate
<range>, driven to the low end by <x>, to the high end by <y>
```

## Exit criteria

The client agrees the problem statement and the commercial shape. Record it in
`signoffs.md` like any other gate — an agreed problem statement is what stops a
requirements conversation from restarting from first principles.
