---
name: build-standards
description: Use when writing code, tests, or reviews on a client engagement, or when deciding whether work meets the firm's definition of done. Also the source content for each client repository's CLAUDE.md. Gate 3 of the greenfield delivery sequence.
---

# Build Standards

The firm's engineering bar. This is also the source content for each client
repository's `CLAUDE.md` — when generating that file at gate 2, this skill is
what you are transcribing.

> **Status:** stack and conventions confirmed 2026-08-08. The **Do not** section
> is seeded with defaults and should grow as engagements teach you things — it
> prevents more damage per line than anything else here.

## The governing principle

**Write for the team that inherits this, not for delivery velocity.**

The client owns this code after handoff. Code they cannot maintain generates
support burden the firm is not paid for, and it is the fastest way for a
successful delivery to become an unprofitable relationship.

Concretely, when the two conflict:

- Conventional beats clever. A pattern their team recognises beats a better one
  they do not.
- Explicit beats implicit. Magic that saves you keystrokes costs them a day.
- Boring dependencies beat exciting ones. They will be maintaining this without
  you.

This is not licence to over-engineer. See **Do not** — the same principle
forbids speculative abstraction, which is equally unmaintainable.

## This is the standard, not the procedure

What follows is the bar a change is measured against. **How a task actually
gets worked — handed to an agent, verified, reviewed, merged — is
`build-loop`.** The two are used together at gate 3, and the distinction
matters: everything here is a state to be in, and none of it tells you what to
do next.

## Default stack

Deviating is allowed. **Deviating without recording why in `design.md` is not** —
undocumented deviations become unexplainable at handoff and are what stop
engagement #7 from being cheaper than engagement #1.

| Layer | Default | Deviate when |
|---|---|---|
| Language / runtime | TypeScript on Node | The client's team maintains another language and will own this |
| Frontend | React | The client has a standard, or the UI is trivial enough not to need a framework |
| Datastore | Postgres | The data is genuinely not relational, or the client mandates otherwise |
| Migrations | In-repo, applied on deploy | Never — a client who cannot reproduce the schema cannot maintain the system |
| CI | GitHub Actions | The client's code lives elsewhere and their CI is the one they will keep |
| Hosting | Per client | Always — this is the client's operational decision, not the firm's |

Record the actual choices in the client's `CLAUDE.md`, with versions.

## Commands

These strings go **verbatim** into every client `CLAUDE.md`. An agent working
in that repository will run exactly what is written there, so paraphrasing
breaks it.

| Purpose | Command |
|---|---|
| Tests | `npm test` |
| Lint | `npm run lint` |
| Types | `npm run typecheck` |

If a project's commands differ, the project's `CLAUDE.md` is authoritative —
update it there, not here.

## Testing

**Test behaviour at boundaries, not implementation.** Tests coupled to internal
structure break on every refactor and train the client's team to delete them.

| Rule | |
|---|---|
| New behaviour | Ships with tests. No exceptions — this is a merge blocker. |
| Bug fixes | Ship with a regression test that fails before the fix |
| External boundaries | Integration-tested: the datastore, third-party APIs, auth |
| Pure logic | Unit-tested directly |
| Framework glue, generated code, config | Not worth testing — do not pad coverage with it |

**Coverage is a signal, not a target.** Do not add tests to move a number. A
low figure in a critical module is worth investigating; a high figure across
the codebase proves nothing.

**Tests are documentation for the inheriting team.** Name them so a failure
message explains what broke without opening the file.

## Code review

The reviewer **runs** the change. Reading a diff catches typos; running it
catches whether it works.

### Blocks a merge

- Tests failing, or new behaviour without tests
- Lint or type errors
- A security issue — auth, injection, secrets in code, unvalidated input at a
  system boundary
- **Deviation from the approved design that is not recorded** — this is a scope
  and traceability problem, not a style preference
- Acceptance criteria from the work item not actually met

### A comment, not a blocker

Naming, structure preference, style, "I'd have done it differently." Say it
once; do not hold a merge over it.

If a comment matters enough to block, it belongs in the list above — add it
there rather than escalating case by case.

## Conventions

| | |
|---|---|
| Naming | Say what it is. Abbreviations only where the domain already uses them. |
| File layout | Group by feature, not by type. The inheriting team navigates by feature. |
| Errors | Fail loudly at boundaries; do not swallow. An error the client cannot see is one they cannot fix. |
| Logging | Log decisions and failures, not flow. Include enough context to act on without reproducing. |
| Configuration | Environment variables, validated at startup. A missing config should fail on boot, not at 3am on first use. |
| Secrets | Never in the repository. Not in tests, not in fixtures, not in comments. |
| Comments | Only for constraints the code cannot express — a non-obvious *why*. Never what the next line does. |

## Commits and branches

| | |
|---|---|
| Branch | `feat/<ticket-id>-<slug>` — e.g. `feat/ACME-142-csv-export` |
| Commit subject | References the work item; says what changed, imperatively |
| Merge | Squash |
| Who merges | The author, after approval |

The ticket ID in the branch and subject is what makes the delivery record
assemble itself at handoff. It costs nothing and it is the difference between
an audit trail and an archaeology project.

## Definition of done

The checklist a change satisfies before it is reviewable. **This is what an
unattended agent is measured against**, so it must be checkable without
judgment calls.

- [ ] The work item's acceptance criteria are met and demonstrable
- [ ] Tests written and passing (`npm test`)
- [ ] Lint clean (`npm run lint`)
- [ ] Types clean (`npm run typecheck`)
- [ ] No secrets, keys, or client data in the diff
- [ ] Documentation updated if behaviour or setup changed
- [ ] `CLAUDE.md` updated if a convention or command changed
- [ ] Work item updated with what changed

"Demonstrable" means you could show it working in a demo. If you cannot, it is
not done.

## Do not

The traps. Each of these has cost someone a day.

> **Extend this list.** When an engagement teaches you something, add it here —
> this is the section that compounds across engagements, and the one most worth
> maintaining.

- **Do not add a dependency the client's team cannot maintain.** Ask: could
  they patch this themselves in a year? If not, write the fifty lines instead.
- **Do not build for requirements nobody approved.** No extension points,
  plugin systems, or abstraction layers for a second use case that does not
  exist. It is unmaintainable and it is unbilled.
- **Do not add error handling for cases that cannot occur.** Defensive code
  around internal guarantees hides the errors that matter.
- **Do not leave commented-out code.** Git has it. The inheriting team cannot
  tell whether it is dead or pending.
- **Do not silently widen scope.** If the work drifts outside the approved
  requirement, name it — it is a change request, and absorbing it costs margin
  on a fixed-scope engagement.
- **Do not commit anything client-confidential** beyond the code itself — no
  production data in fixtures, no real customer records in tests, no
  screenshots containing personal data.
- **Do not skip the regression test on a bug fix** because the fix is obvious.
  The obvious ones recur.

## Feeding `CLAUDE.md`

At gate 2, this skill's content is transcribed into the client repository's
`CLAUDE.md`, adjusted for that project's actual choices.

Transcribe: the stack with versions, the literal commands, testing rules, the
definition of done, and the **Do not** list plus anything project-specific.

Do not transcribe: the governing principle or the review process — those are
firm-internal.

**A thin `CLAUDE.md` produces generic agent output.** On Atlassian engagements
it is also the gate on whether the unattended tier is usable at all: an
engagement whose `CLAUDE.md` does not encode this content should not have work
items assigned to an agent, because reviewing generic output costs more than
writing the code.
