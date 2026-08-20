#!/usr/bin/env bash
#
# Build a sample engagement you can actually open.
#
#   ./examples/make-sample.sh [target-dir]      (default: /tmp/northwind)
#
# The engagement artifacts are only half the story: /dashboard derives its
# activity feed from git history, so a folder of finished files would show an
# empty feed and demonstrate nothing. This script commits the artifacts in the
# order a real engagement produces them, with dates spread over the past six
# weeks, so the dashboard has something true to read.
#
# Everything here is fictional. Northwind Traders is the long-standing sample
# client name; no real engagement is described.
#
set -euo pipefail

TARGET="${1:-/tmp/northwind}"

if [ -e "$TARGET" ]; then
  echo "refusing to overwrite existing path: $TARGET" >&2
  echo "pass a different target, or remove it first." >&2
  exit 1
fi

command -v git >/dev/null || { echo "git not found" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 1; }

mkdir -p "$TARGET/docs/engagement"
cd "$TARGET"
git init -q -b main
git config user.email "delivery@example.com"
git config user.name "Sample Engagement"

E="docs/engagement"

# Dates are relative to today so the sample never reads as stale, and so the
# feed's "last 7 days" range has something in it whenever you run this.
ago() { python3 -c "
import datetime, sys
d = datetime.datetime.now() - datetime.timedelta(days=int(sys.argv[1]))
print(d.replace(hour=10, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S'))
" "$1"; }

day() { python3 -c "
import datetime, sys
d = datetime.datetime.now() - datetime.timedelta(days=int(sys.argv[1]))
print(d.strftime('%Y-%m-%d'))
" "$1"; }

commit() { # commit <days-ago> <message>
  local when; when="$(ago "$1")"
  git add -A
  GIT_AUTHOR_DATE="$when" GIT_COMMITTER_DATE="$when" \
    git commit -q -m "$2"
}

# ---------------------------------------------------------------------------
# Day -42: /new-engagement. The epic does not exist yet, and the file says so
# rather than inventing one — every skill that reads `(pending)` must stop.
# ---------------------------------------------------------------------------
cat > "$E/engagement.md" <<EOF
# Engagement: Northwind Traders

- **Started:** $(day 42)
- **Shape:** Fixed-scope greenfield MVP, 6 weeks
- **Primary contact:** Dana Whitfield, COO
- **Slack channel:** #northwind-delivery

## Tracker
- type: jira
- site: northwind.atlassian.net
- project: NWT
- epic: (pending)

## Progress reporting
- narrative: confluence
- space: NWT
- page: Delivery Status
- dashboard: (pending)

## Repository
- url: https://github.com/northwind/orders-mvp
- default branch: main
EOF
commit 42 "Start engagement: Northwind Traders"

# ---------------------------------------------------------------------------
# Day -40: Discovery. The problem statement is the gate-1 artifact.
# ---------------------------------------------------------------------------
cat > "$E/discovery.md" <<'EOF'
# Discovery — Northwind Traders

## The problem

Northwind's wholesale customers order by emailing a spreadsheet to a shared
inbox. Three staff re-key those orders into the ERP by hand. At current volume
that is roughly 90 minutes per person per day, and re-keying errors are the
single largest source of credit notes.

## Why now

A new distribution contract raises order volume an estimated 40% in Q4. The
current process does not absorb that without a fourth hire.

## What success looks like

- Wholesale customers place orders without emailing anyone.
- No order is re-keyed by hand.
- Credit notes caused by order-entry errors fall to near zero.

## Constraints

- The ERP is the system of record and is not being replaced.
- Six weeks, fixed scope.
- Customers will not install software or attend training.
EOF
commit 40 "Discovery: problem statement and success criteria"

# ---------------------------------------------------------------------------
# Day -38: Requirements drafted. Acceptance criteria are testable statements,
# not aspirations — that is what the requirements gate checks for.
# ---------------------------------------------------------------------------
cat > "$E/requirements.md" <<'EOF'
# Requirements — Northwind Traders

## Functional

| ID | Requirement | Acceptance criteria |
|---|---|---|
| R1 | Customers submit orders through a web form | A customer with a valid account code can submit a line-item order and receives a confirmation number within 5 seconds |
| R2 | Orders reach the ERP without re-keying | A submitted order appears in the ERP as a draft sales order within 2 minutes, with no manual step |
| R3 | Staff review orders before they are committed | An order stays in draft until a member of the orders team approves it; approvals are attributed and timestamped |
| R4 | Customers see order status | A customer can see submitted, approved and rejected states for their own orders only |
| R5 | Rejected orders explain themselves | A rejection records a reason from a fixed list, shown to the customer within 1 minute |

## Non-functional

| ID | Requirement | Acceptance criteria |
|---|---|---|
| N1 | Availability during business hours | 99.5% measured 07:00-19:00 UK, excluding announced maintenance |
| N2 | Order data is retained | Every submitted order is recoverable for 7 years, including rejected ones |

## Out of scope

| ID | Item | Note |
|---|---|---|
| X1 | Replacing the ERP | The ERP stays the system of record |
| X2 | Customer self-service returns | Named for Q1, not this engagement |
| X3 | Mobile application | The web form is responsive; no native app |
EOF
commit 38 "Requirements: 5 functional, 2 non-functional, 3 out of scope"

# ---------------------------------------------------------------------------
# Day -37 and -35: the first two gates are signed. The Commit column carries
# the SHA the artifact was approved AT, which is the fact that makes the
# record defensible — /dashboard re-checks each approval against it.
# ---------------------------------------------------------------------------
DISCOVERY_SHA="$(git rev-parse --short HEAD~1)"
REQS_SHA="$(git rev-parse --short HEAD)"

cat > "$E/signoffs.md" <<EOF
# Sign-offs

| Gate | Artifact | Commit | Approved by | Date | Evidence |
|---|---|---|---|---|---|
| Discovery | discovery.md | $DISCOVERY_SHA | Dana Whitfield, COO | $(day 37) | https://example.slack.com/archives/C01/p1 |
EOF
commit 37 "Discovery gate signed off by Dana Whitfield"

cat > "$E/signoffs.md" <<EOF
# Sign-offs

| Gate | Artifact | Commit | Approved by | Date | Evidence |
|---|---|---|---|---|---|
| Discovery | discovery.md | $DISCOVERY_SHA | Dana Whitfield, COO | $(day 37) | https://example.slack.com/archives/C01/p1 |
| Requirements | requirements.md | $REQS_SHA | Dana Whitfield, COO | $(day 35) | https://example.slack.com/archives/C01/p2 |
EOF
commit 35 "Requirements gate signed off by Dana Whitfield"

# ---------------------------------------------------------------------------
# Day -33: the epic now exists, so the placeholder is replaced with the real
# key. This is the point /sync-tracker becomes usable at all.
# ---------------------------------------------------------------------------
python3 - <<'PY'
import pathlib
p = pathlib.Path("docs/engagement/engagement.md")
p.write_text(p.read_text().replace("epic: (pending)", "epic: NWT-142"))
PY
commit 33 "Tracker epic created: NWT-142"

# ---------------------------------------------------------------------------
# Day -31: design, then the task breakdown produced from approved requirements.
# Every task names exactly one requirement; a blank cell would be malformed.
# ---------------------------------------------------------------------------
cat > "$E/design.md" <<'EOF'
# Architecture — Northwind Traders

## Shape

A small web application in front of the existing ERP. Three parts:

1. **Order form** — server-rendered, no customer install, responsive.
2. **Order service** — validates, persists, and pushes drafts to the ERP.
3. **Review queue** — internal, where the orders team approves or rejects.

## Decisions

| Decision | Why | Alternative rejected |
|---|---|---|
| Push to ERP as *draft* sales orders | Keeps the ERP the system of record and leaves a human in the loop | Direct commit — no reviewer, and errors reach invoicing |
| Server-rendered form | Customers will not install anything; no build step to hand over | SPA — heavier handover for no gain at this scope |
| Own order table, not ERP-only | Rejected orders must survive; the ERP discards drafts | ERP as sole store — fails N2 |

## Handover shape

One repository, one deployment, one database. The orders team owns the review
queue; nothing in the customer path requires the delivery team after handover.
EOF
commit 31 "Design: order form, order service, review queue"

cat > "$E/tasks.md" <<'EOF'
# Tasks — Northwind Traders

Produced at gate 2 from the approved `requirements.md`.

| ID | Task | Req | Owner | Status | Item |
|---|---|---|---|---|---|
| T1 | Add customer account lookup | R1 | Priya Nair | todo | (pending) |
| T2 | Add order entry form | R1 | Sam Okoro | todo | (pending) |
| T3 | Add order submission endpoint | R1 | (unassigned) | todo | (pending) |
| T4 | Add ERP draft order push | R2 | Priya Nair | todo | (pending) |
| T5 | Add review queue list | R3 | Sam Okoro | todo | (pending) |
| T6 | Add approve and reject actions | R3 | (unassigned) | todo | (pending) |
| T7 | Add customer order status view | R4 | Priya Nair | todo | (pending) |
| T8 | Add rejection reason capture | R5 | Sam Okoro | todo | (pending) |
| T9 | Add order retention export | N2 | (unassigned) | todo | (pending) |
EOF
commit 31 "Tasks: 9 work items from approved requirements"

# Test cases come from the SAME approved requirements, at the same gate, so
# they are pinned to the signed baseline rather than to a moving document.
# N1 (availability) deliberately gets none — it is the requirement that was
# written down and then forgotten by both the plan and the tests, which is
# what /conform's C2 rule exists to surface.
cat > "$E/test-cases.md" <<'EOF'
# Test cases — Northwind Traders

Written from `requirements.md` as approved at the Requirements gate.

| ID | Req | Mode | Scenario | Given | When | Then | Result |
|---|---|---|---|---|---|---|---|
| TC1 | R1 | automated | Submit a valid wholesale order | Account NW-4471 is active | The customer submits a 3-line order | A confirmation number appears within 5 seconds | pass |
| TC2 | R1 | automated | Submit against a closed account | Account NW-9902 is closed | The customer submits any order | The order is refused, naming the closed account | pass |
| TC3 | R2 | automated | Order reaches the ERP without re-keying | TC1 has produced a confirmation number | Two minutes pass | The order is a draft sales order in the ERP, entered by nobody | not run |
| TC4 | R3 | automated | Approve an order | An order is awaiting review | Priya approves it | The order leaves draft, showing Priya and the time | pass |
| TC5 | R3 | manual | Orders stay in draft until approved | An order was submitted an hour ago and not reviewed | The orders team looks at the ERP | It is still a draft and has not been invoiced | pass |
| TC6 | R4 | automated | A customer sees only their own orders | NW-4471 and NW-5510 both have orders | NW-4471 opens order status | Only NW-4471 orders are listed | pass |
| TC7 | R5 | automated | Reject an order with a reason | An order is awaiting review | Priya rejects it as "Credit limit exceeded" | The customer sees that reason within 1 minute | fail |
| TC8 | N2 | manual | A rejected order is still retrievable | TC7 has rejected an order | The orders team searches for it a day later | The order and its rejection reason are both retrievable | blocked |
EOF
commit 31 "Test cases: 8 scenarios from approved requirements"

# The working decisions the signed baseline left open. D3 reverses D1 by
# appending rather than editing it — the record has to show that a choice was
# made, for a reason that seemed good at the time, and later changed.
cat > "$E/decisions.md" <<'EOF'
# Decisions — Northwind Traders

Working decisions made between gates. These do not change the signed baseline;
a decision that does belongs in `design.md` and needs the client to re-approve.

| ID | Date | Decision | Why | Instead of | Decided by |
|---|---|---|---|---|---|
| D1 | 2026-07-22 | Poll the ERP every 60s for draft acknowledgement | Their ERP has no webhook and IT will not open one inside this engagement | A webhook, which the design left open | Delivery team with N. Osei, IT |
| D2 | 2026-07-29 | Rejection reasons are a fixed list, not free text | Free text cannot be reported on, and R5 says "from an agreed list" | Free text with a suggested list | Delivery team with Dana Whitfield |
| D3 | 2026-08-06 | Replace the 60s poll with the ERP's file drop | IT surfaced an existing hourly export we did not know about; it removes the poll entirely | Continuing to poll, per D1 | N. Osei, IT — reverses D1 |
EOF
commit 31 "Decisions: three working decisions, one reversing an earlier one"

DESIGN_SHA="$(git rev-parse --short HEAD~1)"
cat >> "$E/signoffs.md" <<EOF
| Design | design.md | $DESIGN_SHA | Dana Whitfield, COO | $(day 30) | https://example.slack.com/archives/C01/p3 |
EOF
commit 30 "Design gate signed off by Dana Whitfield"

# ---------------------------------------------------------------------------
# Day -28: /sync-tracker creates the work items, so the placeholders become
# real IDs. Nothing here invents an ID that the tracker did not return.
# ---------------------------------------------------------------------------
python3 - <<'PY'
import pathlib
p = pathlib.Path("docs/engagement/tasks.md")
s = p.read_text()
for n in range(1, 10):
    s = s.replace(f"| T{n} | ", f"|~T{n}~| ", 1)
s = s.replace("(pending)", "PLACEHOLDER")
ids = {f"~T{n}~": f"NWT-{100 + n}" for n in range(1, 10)}
out = []
for line in s.splitlines():
    for marker, item in ids.items():
        if marker in line:
            line = line.replace(marker, f" {marker.strip('~')} ").replace("PLACEHOLDER", item)
    out.append(line)
p.write_text("\n".join(out) + "\n")
PY
commit 28 "Sync tasks to Jira: NWT-101 through NWT-109"

# ---------------------------------------------------------------------------
# Build. Tasks move; the feed shows each transition.
# ---------------------------------------------------------------------------
set_status() { # set_status <task-id> <status>
  python3 - "$1" "$2" <<'PY'
import pathlib, sys, re
task, status = sys.argv[1], sys.argv[2]
p = pathlib.Path("docs/engagement/tasks.md")
out = []
for line in p.read_text().splitlines():
    cells = [c.strip() for c in line.split("|")]
    # Status is located by header position, not a hardcoded index — adding the
    # Owner column silently shifted it and every set_status became a no-op,
    # which surfaced as "nothing to commit" rather than as a wrong value.
    if len(cells) == 8 and cells[1] == task:
        cells[5] = status
        line = "| " + " | ".join(cells[1:7]) + " |"
    out.append(line)
p.write_text("\n".join(out) + "\n")
PY
}

set_status T1 in-progress; set_status T2 in-progress
commit 26 "Start account lookup and order form"

set_status T1 done
commit 24 "Customer account lookup complete"

set_status T2 done; set_status T3 in-progress
commit 21 "Order entry form complete; start submission endpoint"

set_status T3 done; set_status T4 in-progress
commit 18 "Submission endpoint complete; start ERP push"

# The ERP sandbox is unavailable — a blocked task is the honest state, and the
# dashboard surfaces it rather than letting it look like slow progress.
set_status T4 blocked
commit 16 "ERP push blocked: sandbox credentials not yet issued"

set_status T5 in-progress
commit 14 "Start review queue list"

# -------------------------------------------------------------------------
# Day -12: the client asks for a change to an ALREADY SIGNED requirement.
# This is the event the methodology exists to catch: /dashboard flags it as
# scope drift against a signed baseline, because R5's criterion moved after
# the Requirements gate was approved at $REQS_SHA.
# -------------------------------------------------------------------------
python3 - <<'PY'
import pathlib
p = pathlib.Path("docs/engagement/requirements.md")
p.write_text(p.read_text().replace(
    "A rejection records a reason from a fixed list, shown to the customer within 1 minute",
    "A rejection records a reason from a fixed list plus free-text notes, shown to the customer within 1 minute and emailed to their account contact",
))
PY
commit 12 "R5: client asks for free-text notes and email on rejection"

# The change creates work that was never in the approved breakdown. It is
# appended, never renumbered, and it starts life unlinked to a tracker item.
python3 - <<'PY'
import pathlib
p = pathlib.Path("docs/engagement/tasks.md")
p.write_text(p.read_text().rstrip("\n")
             + "\n| T10 | Add rejection notification email | R5 | (unassigned) | todo | (pending) |\n")
PY
commit 12 "Add T10 for the rejection email R5 now requires"

set_status T5 done; set_status T6 in-progress
commit 10 "Review queue complete; start approve and reject"

# T9 is cut. The row stays and becomes `dropped` — deleting it would shrink
# the denominator and make completion jump with nothing recording the cut.
set_status T9 dropped
commit 8 "Drop retention export: deferred to Q1 by agreement"

set_status T6 done; set_status T7 in-progress
commit 5 "Approve and reject complete; start customer status view"

set_status T4 in-progress
commit 3 "ERP sandbox credentials issued; unblock ERP push"

set_status T7 done; set_status T8 in-progress
commit 2 "Customer status view complete; start rejection reasons"

# Blocked on the client, and left blocked: a live engagement almost always has
# one of these, and it is what the attention panel exists to surface.
set_status T8 blocked
commit 1 "Rejection reasons blocked: awaiting the agreed reason list from R5"

echo
echo "Sample engagement built: $TARGET"
echo
echo "  $(git -C "$TARGET" rev-list --count HEAD) commits over the past 6 weeks"
echo
echo "Open it with:"
echo
echo "    python3 -u scripts/dashboard --root $TARGET"
echo
echo "Things worth looking at:"
echo "  - the activity feed, derived entirely from the git history above:"
echo "    53 events across every kind the dashboard knows about"
echo "  - R5's criterion changed AFTER the Requirements gate was signed, so the"
echo "    approval on record no longer covers the file. That is the CRITICAL at"
echo "    the top of the attention panel, and the reason the Commit column exists."
echo "  - N2 (7-year retention) has no live tasks left. Its only task, T9, was"
echo "    dropped by agreement — so a signed requirement quietly lost its"
echo "    coverage. Dropping rather than deleting the row is what makes that"
echo "    visible instead of just shrinking the denominator."
echo "  - N1 has no tasks at all AND no test case. It was written down once and"
echo "    then forgotten by both the plan and the tests — which is why"
echo "    scripts/conform.py reports two failures on this engagement, not one."
echo "  - TC7 failed and TC8 is blocked; TC3 was never run. At handoff those"
echo "    are three different claims, and none of them is 'passed'."
echo "  - T8 is blocked, and T4 shows a 13-day block ending in the feed"
echo "  - T10 was created by the R5 change and has no tracker item yet"
