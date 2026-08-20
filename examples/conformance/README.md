# Conformance fixtures

Each directory is an engagement that breaks exactly one rule, so
`scripts/conform.py` can be shown to *discriminate* rather than merely to run.
A checker that never fails is not a checker.

| Fixture | Expected |
|---|---|
| `gate-out-of-order/` | `G1` fails — Design is signed, Requirements is not |
| `missing-commit/` | `G2` fails — a sign-off points at a commit that does not exist |
| `duplicate-req-id/` | `R2` fails — two requirements share an ID |
| `no-criterion/` | `R3` fails — an in-scope requirement states no way to check it |
| `dangling-task/` | `T3` fails — a task points at a requirement that was never written |
| `untested-requirement/` | `C2` fails — R2 has no test case, so it can only be assumed met |
| `not-started/` | nothing fails; every rule but `E1` reports `skip` |
| `scaffolded/` | nothing fails; only the three well-formed checks pass |

`scaffolded/` is exactly what `/new-engagement` writes: correct files with
empty tables. It caught a real defect — every rule over an empty collection was
trivially true, so a day-one engagement reported **10 passed, 0 failed** before
anyone had written a requirement. An empty table is not a passing table, and
`present` is not the same as `has rows`.

`not-started/` is the one that matters most. A brand-new engagement has no
requirements, no tasks and no sign-offs, and it must report those as **not
checked** rather than as passes. A tool that grades an empty engagement as
compliant is worse than no tool.

The realistic case lives elsewhere: `examples/make-sample.sh` builds an
engagement that fails `G3`, because a requirement's acceptance criterion was
changed after the client approved it. That is not a defect in the fixture — it
is the finding the methodology exists to produce.
