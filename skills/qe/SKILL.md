---
name: qe
description: Use when automating business test cases - generating Gherkin feature files from test-cases.md, deciding what should and should not be automated, wiring step definitions in the client repository, and reading run results back into the engagement record.
---

# QE

Turning business test cases into an executable suite, without losing the thing
that made them worth writing.

**QE is not a gate.** A gate produces a durable artifact requiring recorded
*client* approval, and no client approves your step definitions. QE runs inside
Build, and its results are the acceptance evidence the `handoff` gate presents.
Adding a sixth gate would ask the client to sign off on your internal
engineering, which invites the wrong conversation and blurs a five-gate spine
that currently fits on one page.

## The direction is the design

Feature files are generated **from** `test-cases.md`. Never the reverse.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/features.py" generate --root . --out features/
```

Author Gherkin first and the developers own the specification: the business
stops reading it, and you have paid the full cost of a translation layer for
none of its benefit. That is how BDD usually dies. `test-cases.md` stays the
source of truth and stays readable by the client.

Generated files carry a "do not edit" banner and are disposable. **If someone
improves the wording, they improve the test case and regenerate.** A change made
only in a `.feature` file is lost on the next run and, worse, silently
disagrees with the document the client is accepting against.

## Where the runner lives

**In the client's repository, in the client's stack — never here.**

This plugin adds no dependencies, and a test runner is a dependency tree:
Cucumber or Behave or pytest-bdd, plus a browser driver, per language, per
version. Owning that in the plugin would cost exactly what the plugin exists to
avoid. The boundary is:

| Here | The client repository |
|---|---|
| `test-cases.md` — the source of truth | `features/` — generated, disposable |
| the generator | step definitions |
| reading results back | the runner, the CI job, the browser driver |

Step definitions are ordinary code and belong under `build-standards` like any
other code in the engagement.

## What to automate, and what not to

Every case carries a `Mode`: `manual` or `automated`. It is **stated, never
inferred** from whether a feature file happens to exist — inferring it makes
"nobody wired this up yet" indistinguishable from "a person runs this
deliberately".

Automate a case when a machine can observe the same thing the business user
would. Leave it manual when it cannot:

- **Leave manual** anything whose result is a judgment — is the rejection
  wording clear enough to send to a customer, does the export look right to
  the finance team.
- **Leave manual** anything that needs a person to be present: a phone call, a
  physical scan, a third party's sandbox that only opens on request.
- **Do not automate what cannot honestly be proved.** Availability of 99.5%
  and seven-year retention cannot be demonstrated by a scenario inside a
  six-week engagement. Say so, and say what *will* be checked instead.

That last one is where this pipeline turns dangerous. A rule that every case
must be automated produces scenarios asserting something trivially true, marked
`pass`, and believed **because they are automated**. That is a manufactured
green with a machine's authority behind it — worse than an empty column.

## Reading results back

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/features.py" results --root . --report cucumber.json
```

Cucumber JSON is the one report format the common runners agree on, so this
works whichever the client's stack uses. Scenarios map back by their `@TC` tag,
not by scenario text — text should be free to improve without breaking the
mapping.

Three behaviours worth knowing, because each is a place a suite could lie:

- **An undefined or pending step is `not run`, not `pass`.** A step nobody
  implemented has not proved anything.
- **An empty scenario is `not run`.** It trivially has no failing step, and
  reading that as a pass is how a suite reports green having verified nothing.
- **A case absent from the report keeps the result it had.** Absence from a
  report is not evidence. Automated cases the runner never mentioned are named
  in the output rather than counted, because they are usually scenarios nobody
  wrote steps for — invisible in any summary that reports only passes.

Manual cases are never touched by an import. A person records those.

## Checking it

`/conform` covers this:

| Rule | Fails when |
|---|---|
| `C1` | `test-cases.md` is not well-formed |
| `C2` | an in-scope requirement has no test case at all |
| `C3` | the suite runs, but some automated cases never do |

`C3` is the one this pipeline needs, and it deliberately does **not** fire
while the suite is being built. Three states:

- **No automated cases** — nothing to check.
- **No automated case has run yet** — the suite is not wired up. That is the
  ordinary state from the Design gate until someone writes step definitions,
  and failing throughout would leave this red for the whole build phase. A
  check that is always red is one a team learns to ignore, and then it is not
  a check.
- **Some have run and some have not** — the suite is live and these are being
  skipped inside a run that reports green on everything else. That is the
  defect, and nothing else in the engagement would notice it.

A `fail` is not a stalled case. The suite ran it and it did not pass; that is a
conversation, not a gap in the suite.

## At handoff

Bring the run, not a summary of it: how many cases ran, how many passed, every
`fail` and `blocked` with what was decided, the manual cases and who ran them,
and the requirements with no case at all.

**Never present an automated suite as acceptance evidence without saying what
it did not cover.** An automated pass is more persuasive than a manual one and
deserves more scrutiny, not less — it is trusted precisely to the degree nobody
re-reads it.
