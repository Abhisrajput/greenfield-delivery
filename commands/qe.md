---
description: Generate Gherkin feature files from the business test cases, or read run results back
argument-hint: generate | results <path to cucumber.json>
---

# QE

Use the `qe` skill for the reasoning. This command is the mechanics.

## 1. Check the inputs

Read `docs/engagement/test-cases.md`.

**If it does not exist, stop and say so.** There is nothing to generate from —
test cases come from approved requirements at the Design gate. Offer the
`business-test-cases` skill; do not write feature files from `requirements.md`
directly, and do not invent scenarios.

**If no argument was given, stop and ask** which of `generate` or `results` is
wanted. They are not interchangeable: one writes feature files, the other
rewrites the engagement record.

## 2. Generate

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/features.py" generate --root . --out features/
```

One file per requirement, each scenario tagged with its case ID, its
requirement, and its mode.

It **refuses to generate from a file with row-level problems** rather than
silently dropping the rows it could not read — a suite that looks complete
while missing cases is the failure this step is guarding against. Report the
problems and fix `test-cases.md` first.

Generated files carry a "do not edit" banner. Say so when reporting: a change
made in a `.feature` file is lost at the next regeneration and disagrees with
the document the client accepts against.

## 3. Read results back

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/features.py" results --root . --report <cucumber.json>
```

**This writes to `docs/engagement/test-cases.md`.** It is the one command here
that does. Say what changed and how many rows.

Report the "automated but absent from the report" line verbatim if it appears.
Those are cases with a feature file and no step definitions behind them, and
they are invisible in a runner summary that reports only what it ran.

**Never edit a `Result` cell by hand to match what you expect.** A result is a
record that something was executed. If the runner did not report a case, it did
not run — say that rather than filling it in.

## 4. Then check it

Run `/conform`. `C3` stays quiet while the suite is being built — every
automated case at `not run` means nobody has written step definitions yet,
which is ordinary. It fires once **some** automated cases have run and others
still have not: those are being skipped inside a run that reports green on
everything else, and no runner summary will mention them.
