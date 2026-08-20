# Greenfield Delivery — Agent Instructions

This repository is a Claude Code plugin encoding a greenfield delivery
methodology. It is primarily consumed through Claude Code's skill system, but
this file exists so that other agent tools get the methodology in a usable, if
degraded, form.

## If you are working on an engagement

Read `skills/greenfield-delivery/SKILL.md` first. It is the spine: it defines
the gate sequence, the rule that gates are sequential and require recorded
client approval, and which other skill applies at each step.

Then read the skill for the gate you are on:

| Gate | Skill |
|---|---|
| Discovery | `skills/discovery/SKILL.md` |
| Requirements | `skills/requirements-gate/SKILL.md` |
| Design | `skills/architecture-design/SKILL.md` |
| Build | `skills/build-standards/SKILL.md` |
| Handoff | `skills/handoff/SKILL.md` |

Tracker work is covered by `skills/tracker-conventions/SKILL.md` plus the
skill for the specific tracker named in the engagement's `engagement.md`.

## The non-negotiable rule

**Gates are sequential and each requires recorded client approval before the
next begins.** Approval is recorded in `docs/engagement/signoffs.md` with the
commit SHA of the approved artifact. Do not begin design work before
requirements are signed off, and do not begin build work before design is
signed off.

If you are asked to skip ahead, say so plainly and ask for the approval to be
recorded first.

## If you are working on this plugin itself

Skills are markdown. There is no build step, no dependency install, and no test
runner. Changes take effect when the plugin is reinstalled or the repo is
pulled.

Keep skills short. They are loaded into context on trigger, so length is a cost
paid on every engagement.

### Run the checks

```
./scripts/check.sh
```

Pure bash and python3, no dependencies. Run it after adding or editing any
command, skill, or subagent.

### The dashboard and the conformance checker are the code here

`scripts/dashboard/` is python3 stdlib only, and `parse`, `analyse`, and
`render` are pure functions with no I/O. Keep it that way: the tests depend on
it, and the git and HTTP layers are the only places a failure can hide.

`scripts/conform.py` follows the same split: `check_all` is pure and takes
parsed files; every file read and git call lives in `main`. It reuses
`dashboard.parse` and `dashboard.analyse` rather than carrying a second copy of
the parsing rules — if the two ever disagree about what a valid `tasks.md` is,
the disagreement is the bug.

Its three outcomes are load-bearing: `pass`, `fail`, and `skip` for a rule that
could not be checked. **A skip must never be reported as a pass.** A checker
that grades a brand-new engagement as compliant certifies every engagement on
its first day, which is worse than having no checker. `examples/conformance/`
holds one fixture per rule, each breaking exactly one, and `check.sh` fails if
any fixture stops failing its rule — that is what keeps the checker able to
discriminate rather than merely able to run.

Its governing rule is the same one behind `check.sh` — **no unknown state may
render as a confident value.** Absent, empty, and malformed are three different
displays, and an unverifiable sign-off never shows a tick. If you add a panel,
add its unknown state first.

This repo runs **Python 3.9.6**. Every module in `scripts/dashboard/` opens
with `from __future__ import annotations`, which is what makes `str | None`
and `tuple[Task, ...]`-style annotations parse at all on 3.9 — the future
import rescues annotations only. A union evaluated at *runtime*
(`isinstance(x, int | None)`, a union as a default value or dict value, etc.)
still raises `TypeError` regardless of the future import. `itertools.pairwise`
is 3.10+ too; write an explicit index loop or `zip(xs, xs[1:])` instead. Any
new module here keeps the same future import.

`events.py` is pure like `parse` and `analyse`: it takes two parsed file
versions plus commit metadata and returns events. All git access stays in
`history.py`, and the clock stays in `serve.py`.

Events cache on `HEAD` alone, separately from `State`. Editing a file without
committing must not re-walk history — that walk is the most expensive thing
this product does.

### The client script is gated by a by-hand check, not by tests

`FEED_JS` and `THEME_JS` are verified by running the page in a browser at
implementation time and by nothing afterwards. The Python suite has no
JavaScript runtime: it pins the strings and attributes the script depends on,
but it never executes the logic. A regression where the logic breaks while
those strings stay put would pass every test.

This is a deliberate trade, not an oversight. Pinning the behaviour needs a JS
runtime, which means node and a dependency tree — and the plugin's economics
rest on not having one. So if you change the client script, **run the page**:
the range filter, the first-visit case with `localStorage` cleared, the task
chips, and one load with JavaScript disabled. Three defects on this branch
reached a fully green suite and were caught only that way, including one where
the entire feed was missing from the page.

### Why the guard check matters

`check.sh` fails any command that has no stop condition. This is not style
enforcement — it encodes the failure pattern behind every serious defect found
in this plugin so far.

Eight defects were found across three review passes before first client use.
Every high-severity one had the same shape: **an action that fails silently in
the wrong direction.**

| Defect | What the agent would have done |
|---|---|
| No canonical `engagement.md` format | Invented block names other skills read |
| No `(pending)` convention for `epic:` | Invented an epic ID; work items parented to an unrelated live ticket |
| No target check in `/status-report` | Written a status page into the wrong client's Confluence space |
| No baseline check in `/handoff` | Asserted verified requirement coverage against nothing |

None of these throw an error. All of them look like success and surface days
later, on a client engagement.

**So when you add a command, ask the question the check is a proxy for:** for
every input it reads, what happens when that input is missing, malformed, or
belongs to a different engagement? If the answer is "it proceeds," add a stop
condition.

Two rules that fall out of this, worth applying without being asked:

- **Never fall back to a different target** because the configured one looks
  unavailable. A missing Confluence space means stop, not write somewhere else.
- **Never invent an identifier.** Tracker IDs, project keys, and URLs are
  either read from `engagement.md` or asked for.
