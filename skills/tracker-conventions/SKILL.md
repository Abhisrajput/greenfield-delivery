---
name: tracker-conventions
description: Use when creating or reviewing work items, tickets, stories, or backlog items on a client engagement - including deciding whether an item is well-specified enough to assign to an agent. Tracker-agnostic.
---

# Tracker Conventions

The firm's standard for work items, independent of which tracker the client
uses. For tracker-specific field names and transitions, see `tracker-jira` or
`tracker-azure-devops` — which one is named in `docs/engagement/engagement.md`.

## Why this matters more than it looks

Agents work from work-item context. On Atlassian engagements, a well-specified
item can be assigned to Claude and come back as a draft pull request — which
means **item quality is the ceiling on unattended output quality.** A vague
item produces a vague pull request, and reviewing that costs more than writing
the code would have.

## Item structure

### Title

`<verb> <object>` — what will be true when it is done. Not a topic.

**Weak:** "Order export"
**Strong:** "Add CSV export to the order list"

### Body

| Section | Content |
|---|---|
| Requirement | The `R<n>` this serves. Every item traces to a numbered requirement. |
| Context | What a developer needs who has not read the design doc |
| Acceptance criteria | Copied from `requirements.md`, not paraphrased |
| Out of scope | What this item explicitly does not cover |

**Copy acceptance criteria verbatim.** Paraphrasing is where scope drifts —
the tracker and the signed baseline must agree word for word, or a dispute has
two conflicting sources.

## Traceability

Every item names its requirement. This gives three things cheaply:

- Coverage — a requirement with no items is unplanned work
- Scope control — an item with no requirement is scope creep, visible early
- Handoff — the delivery record assembles itself

## Estimates

**TODO — confirm the firm's scale.** Whatever it is, apply it consistently;
an inconsistent scale is worse than none, because it produces confident wrong
forecasts.

An item too large to estimate is too large to specify. Split it.

## Ready to assign to an agent

Before assigning an item to an agent rather than a person, all of these must
hold:

- [ ] Acceptance criteria are testable without asking the author
- [ ] The change is scoped to a known area of the codebase
- [ ] No architectural decision is required — that belongs in gate 2
- [ ] No ambiguity requiring a client conversation
- [ ] `CLAUDE.md` covers the conventions this change must follow

**Keep with a person when:** the item requires a judgment call, touches
security or auth, changes a public interface, or the acceptance criteria
contain the word "appropriate", "sensible", or "as needed".

Those words are a reliable signal that the item is not actually specified.

## Anti-patterns

| Pattern | Why it fails |
|---|---|
| "Investigate X" | No acceptance criterion, so it cannot be finished — only abandoned |
| "Fix bugs from testing" | Unbounded; becomes a dumping ground |
| Criteria only in a comment thread | An agent reads the item, not the thread |
| Item with no requirement link | Invisible scope creep |
| Compound item ("add export and scheduling") | Cannot be partially accepted |
