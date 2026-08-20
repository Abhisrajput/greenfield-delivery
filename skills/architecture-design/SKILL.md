---
name: architecture-design
description: Use when producing the engagement design document, choosing architecture or stack for a client project, or generating the client repository's CLAUDE.md and AGENTS.md. Gate 2 of the greenfield delivery sequence.
---

# Architecture & Design

Gate 2. Produces four artifacts from one agreed design:

1. `docs/engagement/design.md` — the client-facing design document
2. `CLAUDE.md` — the client repository's agent configuration
3. `AGENTS.md` — a pointer to `CLAUDE.md` for non-Claude tools
4. `docs/engagement/tasks.md` — the approved requirements broken into a task
   list. This is a design output, not a build output: deciding the units of
   work is a design decision. Gate 3 works the list down, and `/sync-tracker`
   translates it into tracker work items.

Use the canonical `tasks.md` format in the `greenfield-delivery` skill. Do not
invent it — three commands read this file by exact column name.

Every task names the requirement (`R<n>`) it serves. A task with no requirement
is scope creep; a requirement with no task is unplanned work. Both are visible
immediately if the list is written this way.

## Design document

Written for a technical reader on the client side who has to approve it. Cover:

- **Architecture** — components, responsibilities, how they communicate
- **Stack** — with the reason for each significant choice, and what was
  rejected. A design that only lists what was chosen cannot be evaluated.
- **Data model** — entities and relationships, at the level the requirements need
- **Key decisions** — each with the trade-off accepted
- **Requirement traceability** — which requirements each component serves. Any
  requirement with no component is a gap; any component serving no requirement
  is scope creep.

Use the `architect` subagent for proposals. It gives options with trade-offs and
a recommendation, which is the shape clients approve most easily.

### Deviating from the firm default stack

The default stack lives in `build-standards`. Deviating is fine, but record why
in the design document. Undocumented deviations become unexplainable at
handoff, and they are what makes engagement #7 as expensive as engagement #1.

## `CLAUDE.md` — the load-bearing artifact

**This is the most important output of the gate**, and it is easy to
under-invest in because it does not go to the client directly.

Every agent that later touches the client repository reads it — including
Claude Agent for Jira, which is otherwise a generic implementer with no
knowledge of the firm's methodology. `CLAUDE.md` is how the methodology reaches
unattended work without any orchestration infrastructure.

**If `CLAUDE.md` is thin, unattended output is generic.** Treat it as a
deliverable, not a config file.

### What goes in it

| Section | Content |
|---|---|
| Project | What this is, who it is for, in three sentences |
| Architecture | The shape, and where things live |
| Stack | Versions, frameworks, and the constraints on each |
| Conventions | Naming, file layout, error handling, logging |
| Testing | What must be tested, at what level, and how to run it |
| Definition of done | The checklist a change must satisfy before review |
| Do not | The traps specific to this codebase |

The **Do not** section earns its place fastest. Every codebase has decisions
that look wrong without context; writing them down is what stops an agent
"fixing" them.

Split it in two: the firm-wide list transcribed from `build-standards`, then a
`### Project-specific` subsection for this codebase's own traps — licence
restrictions, upstream quirks, data assumptions that do not hold. The
project-specific half is where the real value is, and separating them makes it
obvious when it is empty, which usually means nobody has thought about it yet.

### Write it from the agreed design, not from the code

`CLAUDE.md` is generated at gate 2, before the build. It encodes what was
agreed, which is what makes the build conform to it rather than the reverse.
Update it when the design genuinely changes — and when it does, that is a
design change, which may be a change request.

## `AGENTS.md`

**A pointer, not a copy.** Two files carrying the same conventions will drift,
and drifted conventions are worse than one file.

```markdown
# Agent Instructions

This project's conventions, architecture, stack, testing expectations, and
definition of done are documented in [CLAUDE.md](./CLAUDE.md). Read that file
before making changes.
```

That is the whole file. Its value is that after handoff, the client's team may
use a different agent tool — and it will still be pointed at the same standard.

## Sign-off

The client approves architecture and stack. Prepare the Slack post as with
requirements, record the row in `signoffs.md` with the commit SHA, then break
the stories into work items via `/sync-tracker`.
