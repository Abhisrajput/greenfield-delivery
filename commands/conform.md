---
description: Check this engagement's record against the rules the methodology states
argument-hint: none
---

# Conform

Run the conformance checks over `docs/engagement/` and report what holds, what
is broken, and what could not be checked.

## 1. Check this is an engagement

Read `docs/engagement/engagement.md`.

**If it does not exist, stop and say so.** This is not an engagement — offer
`/new-engagement`. Do not run the checker against an empty directory and do not
guess at another location.

## 2. Run it

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/conform.py" --root .
```

It exits `1` if any check failed and `0` otherwise. It reads only; it never
writes to `docs/engagement/`.

## 3. Report it honestly

Three outcomes, and they are not two:

| Outcome | Means |
|---|---|
| `PASS` | the rule was checked and holds |
| `FAIL` | the rule was checked and is broken |
| `skip` | the rule **could not** be checked |

**Never describe a `skip` as a pass, and never summarise a run as "all checks
passed" when any were skipped.** A new engagement skips nearly everything —
that is correct and expected, and reporting it as compliance would certify
every engagement on its first day. Say how many were not checked and why.

State plainly what the run does not cover: it checks that the record is
well-formed and internally consistent. It cannot tell whether a requirement is
the *right* requirement, and an engagement can pass every check and still be
badly run.

## 4. When something failed

Report the rule and the detail verbatim, then say what would fix it. Do not fix
it silently — several of these failures are conversations with the client, not
edits:

- **G3 (an approved artifact changed)** is a change-order conversation. Do not
  re-sign the gate to make the check pass. Recording a fresh approval the client
  never gave is the one failure this methodology exists to prevent.
- **G1 (gates out of order)** usually means an approval happened out of band.
  Record it with its evidence, or close the earlier gate properly.
- **R3 (a requirement with no acceptance criterion)** means the requirements
  gate has work left. An untestable requirement is one nobody can accept.

Do not invent a commit SHA, a date, or an approver to satisfy a check.
