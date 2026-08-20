# Contributing

Greenfield is a methodology encoded as markdown, plus one small Python
dashboard. Contributions are welcome; the constraints below are what keep it
cheap to own, and they are not negotiable in a pull request.

## The constraints

**Skills, commands and agents are markdown.** No build step, no bundler, no
generated files. If a change requires a toolchain to produce, it does not
belong here.

**The dashboard is Python 3.9+, standard library only.** No pip, no npm, no
CDN. It binds `127.0.0.1`, serves `GET` only, and never writes to
`docs/engagement/`. A dependency is a fork to rebase later; that is the cost
this project exists to avoid.

**Never invent an identifier.** Tracker IDs, project keys and commit SHAs are
read from files or reported missing. `None` means "cannot tell" and must never
render as zero. Most of the defects found in this codebase were a confident
answer where the honest answer was "I don't know" — a fabricated tracker ID
sends someone to a ticket that does not exist.

**Purity boundaries.** `parse.py`, `analyse.py`, `events.py` and `render.py`
are pure functions. `history.py` owns every git call. `serve.py` owns HTTP,
the filesystem and the clock. Tests depend on this.

## Running the tests

```
cd scripts && python3 -m unittest discover -p 'test_*.py'
./scripts/check.sh
```

Run them from `scripts/`. From the repository root you get
`ModuleNotFoundError`, which looks like a failure and proves nothing.

## Tests must be able to fail

Before submitting a test, break the code it covers and confirm it fails. This
is asked for a reason: several tests in this repository's history passed
against deliberately broken builds — a sort test comparing two commits made in
the same second, an assertion that a page did not say "0" which also passed
when the page said nothing at all. A test that cannot fail is worse than no
test, because it reports safety.

## Reporting a defect

The useful report is a scenario, not a diagnosis: the engagement state, what
the dashboard showed, and what was actually true. The worst defects in this
project were all of one kind — the product stating something false with
confidence — and they are easiest to see from the outside.
