---
description: Open the read-only engagement dashboard in a browser
argument-hint: Optional - port number
---

# Dashboard

Serve a local, read-only view of this engagement: gate sign-off state, task
progress and trend, requirement coverage, and anything needing attention.

## 1. Check this is an engagement

Read `docs/engagement/engagement.md`.

**If it does not exist, stop and say so.** This is not an engagement — offer
`/new-engagement`. Do not start the server against an empty directory and do
not guess at another location.

## 2. Start it

Run in the background:

```
python3 -u "${CLAUDE_PLUGIN_ROOT}/scripts/dashboard" --root .
```

The `-u` flag matters when this runs in the background: without it, Python
block-buffers stdout because it is not attached to a terminal, and the two
lines below never reach the captured output for as long as the server keeps
running.

It binds `127.0.0.1` only and serves `GET` only — it never writes to
`docs/engagement/`. Report the URL it prints. (`HEAD`/`OPTIONS` return 501,
not 405 — correct semantics for a method the server never implements, and a
deliberate deviation from "405 otherwise" for those two verbs specifically.)

If every port in 8420-8429 is taken, it exits saying so. Pass `--port` to
choose another; do not fall back to a different interface.

### Several engagements at once

`--root` takes more than one path:

```
python3 -u "${CLAUDE_PLUGIN_ROOT}/scripts/dashboard" --root ~/clients/acme ~/clients/beta
```

`/` then serves a portfolio index — one row per engagement with its current
gate, task count and worst finding — and each engagement is at `/e/<slug>`,
the slug taken from its directory name.

A path that is not an engagement is **listed on the index saying so**, not
dropped. Report that as well: a portfolio quietly missing a
row is worse than one showing a bad row, because it looks complete.

**If none of the given paths is an engagement, it stops** and names each one.
Do not retry with a guessed path.

### The activity feed

The page opens on **what moved since you last looked**. That baseline lives in
the browser's `localStorage`, so the server holds no memory of who is looking —
which is what keeps the feature compatible with the read-only guarantee.

Range chips switch between since-last-visit, the last 7 days, and all history.
On a first visit there is no baseline, and the feed says so rather than
implying nothing has happened.

If a commit's files cannot be parsed the feed says how many — a feed that
silently drops events looks like a quiet week.

### Seeing what drifted

When an approved artifact has changed since its sign-off, the finding expands
to show the diff between the approved commit and now. That is the question the
finding raises and could not previously answer without leaving for git.

If the approved version cannot be read, it says so rather than showing an empty
diff — "nothing changed" and "the comparison could not be made" are opposite
claims about whether the client's approval still holds.

### Several engagements

With more than one `--root`, every page carries a switcher: each engagement by
client name, and a link back to the portfolio. With a single root there is
nowhere to go, so no navigation is rendered at all.

## 3. Say what it shows

Name the client from `engagement.md` so the reader can confirm the
dashboard is pointed at the engagement they meant. Two dashboards for two
clients look alike apart from that name.
