# Using it

For whoever is running the engagement — product owner, delivery lead, or the
developer who picked it up.

Everything runs in the **client's repository**. The plugin is installed once and
holds no engagement data of its own; the record lives with the code it describes.

---

## The whole engagement on one page

| Gate | What it settles | Produces | Client does | Command |
|---|---|---|---|---|
| **0. Discovery** *(optional)* | Is this worth doing, and what shape | `discovery.md` | Agrees the problem | `/gate discovery` |
| **1. Requirements** | **What we are building** | `requirements.md` | **Approves the scope baseline** | `/gate requirements` |
| **2. Design** | How, and broken into work | `design.md`, `tasks.md`, `test-cases.md`, `CLAUDE.md` | Approves the approach | `/gate design` |
| **3. Build** | The software | working code, results | Sees demos and status | `/gate build`, `/sync-tracker` |
| **4. Handoff** | What was actually delivered | README, runbook, delivery record | Accepts | `/gate handoff` |

**Gates are sequential and each needs recorded client approval before the next
begins.** Approval is recorded against the **commit SHA** of exactly what they
approved — that single fact is what makes everything else here work.

### Who does what

| | Does |
|---|---|
| **Client** | Approves each gate. Nothing else is required of them. |
| **You** (PO or delivery lead) | Runs the gates, takes artifacts to the client, records approvals |
| **Developers** | Work tasks at gate 3, following `CLAUDE.md` |
| **Agents** | Work individual tasks — verified by a person before merge |

---

## See it working first

Two minutes, no client, no tracker:

```
./examples/make-sample.sh /tmp/northwind
python3 -u scripts/dashboard --root /tmp/northwind
```

A finished-looking engagement with the awkward bits real ones have: a
requirement that changed after sign-off, a blocked task, a dropped one.

## Install

```
/plugin marketplace add Abhisrajput/greenfield-delivery
/plugin install greenfield
```

Once per person. You need write access to the client's repository and an account
on their tracker.

---

# Gate 0 — Discovery *(optional)*

**Skip it** when the work is well defined. **Run it** when you are being asked to
price something nobody has articulated yet.

```
/gate discovery
```

**Produces** `discovery.md`: the problem, why now, what success looks like, the
constraints.

Discovery does **not** block Requirements. It gates the commercial shape of the
work, not the scope baseline.

---

# Gate 1 — Requirements

The gate that pays for itself. Everything downstream traces to it.

### Gathering is incremental. Approval is a moment.

Requirements arrive over days, from wherever the client keeps them:

| Input | What to do |
|---|---|
| Conversations | Extract, confirm, add rows |
| A transcript or meeting notes | **Extract as candidates** — see below |
| A document they wrote | `/import-artifact requirements ./their-doc.md` |
| **A Confluence page** | `/import-artifact requirements <page URL or ID>` |

`requirements.md` grows across all of it. **The gate is where you stop and ask
for approval** — not a claim that everything arrived at once.

```
/gate requirements
```

**Produces** `requirements.md` — functional, non-functional, and **out of
scope** — each with an acceptance criterion that can actually be checked. The
out-of-scope list is the one you point at in week five when somebody asks why a
thing they never mentioned isn't there.

**Client approves.** The approval is recorded in `signoffs.md` **with the commit
SHA** of what they approved. From here, that is the baseline.

### How the approval itself works

**Nothing here collects an approval.** No button, no workflow. You ask, the
client answers in the channel they already use, and you write down what happened
— because an approval the tooling generated would be an approval nobody gave.

1. Commit the artifact
2. `/approve <gate> request` drafts the ask — **you send it**, it never sends on
   your behalf
3. The client replies in Slack, email, a meeting, or a Jira comment
4. `/approve <gate>` records it: gate, artifact, **commit SHA**, who approved,
   date, and a link to their reply

The approval usually arrives a day or three later, which is why recording it is
its own command — `/gate` would redo the whole gate to write one row.

**What counts:** an unambiguous yes, from the person named in `engagement.md`,
against *this* commit. Silence is not approval. "No objections" is not approval.
**"Yes, but change R3" is a no with instructions** — change it, commit, ask
again against the new commit.

**Approved verbally in a meeting?** Record it and say so in the evidence column,
then follow up in writing the same day. A verbal approval is real but it is not
evidence, and the difference only matters on the day it is disputed.

### If the source is a transcript

A conversation contains decisions, half-decisions, thinking aloud, and things
said to be polite. Everything extracted is a **candidate** under *Open
questions*, carrying the quote that produced it, until the client confirms it.

**Never write an acceptance criterion the client did not say.** People do not
speak in acceptance criteria — if the transcript has no testable condition, the
criterion is unknown, and unknown goes in the question, not the table.

### A requirement that turns up later

Amend; never edit quietly:

1. Change `requirements.md`, commit it
2. Take it to the client — **this is the change-order conversation**
3. On approval, **append a second row** to `signoffs.md` at the new commit

The original row stays. The record shows that scope moved, when, and who agreed.

---

# Gate 2 — Design

Where the *how* is settled, and where the work is broken out.

```
/gate design
```

**Produces four things:**

| File | What it is | Approved by the client? |
|---|---|---|
| `design.md` | The approach, and decisions with their rejected alternatives | **Yes** |
| `tasks.md` | The work, broken out — every task names exactly one requirement | No — yours |
| `test-cases.md` | How the client will accept it, in business language | No — but they run at handoff |
| `CLAUDE.md` | The conventions **agents** must follow in this repository | No — yours |

`CLAUDE.md` is the technically load-bearing one: it is what makes a generic agent
build things this project's way without being told again each session.

---

# When do tickets get created?

**At gate 2, after the design is approved, by running `/sync-tracker`.**

```
/sync-tracker
```

```
requirements.md        R1, R2, N1 …
      ↓  broken down at gate 2, by you or an agent
tasks.md               T1 → R1, T2 → R1, T3 → R2 …
      ↓  /sync-tracker
Jira    epic  KAN-1                    ← the engagement
        ├── story KAN-2   ← R1         ← one story per REQUIREMENT
        │   ├── subtask KAN-9   ← T1   ← one subtask per TASK
        │   └── subtask KAN-10  ← T2
        └── story KAN-3   ← R2
            └── subtask KAN-11  ← T3
      ↓  real keys written back
tasks.md   | T1 | … | R1 | Priya Nair | in-progress | KAN-9 |
```

**Requirements are not tickets, and the gap is deliberate.** Nothing turns R1
into tickets automatically. Breaking a requirement into work is a *design*
decision — how many pieces, in what order, touching what — and it happens after
the client has agreed what is being built.

**Acceptance criteria are copied verbatim** into each story, so the tracker and
the signed baseline say the same words.

**Until the tracker returns a key, the task reads `(pending)`** — never a guessed
ticket number.

`/sync-tracker` also **pulls back**: current status, and who each item is
assigned to. Run it whenever you want the record to match the tracker.

---

# Gate 3 — Build

Where most of the hours go.

### How a task gets assigned

**Assignment happens in the tracker, not in a file** — that is where the team
already changes it. `/sync-tracker` pulls the assignee into `tasks.md`'s `Owner`
column and the dashboard shows it, so *"who has T7?"* is one screen rather than a
conversation.

A task nobody is on reads `(unassigned)`, never blank: on a team, "nobody is on
this" and "nobody filled this in" need different conversations.

### How one task gets worked

The full loop is the `build-loop` skill. In short:

1. **Check the task is ready** — testable criteria, a known area of the code, no
   architectural decision, no open client question. An unready task produces
   confident work against somebody's guess.
2. **One branch, one task**, with the work item ID in the name
3. **Split the acceptance criterion into clauses.** *"records a reason **and** the
   dispatcher sees it within a minute"* is two pieces of work, and building one
   is the commonest way to half-finish a requirement
4. **Build**
5. **Verify by driving it** — open the page, call the endpoint, click the control.
   A green suite says nothing about whether the feature is *reachable*
6. **Review** — agent code fails differently from human code: plausible,
   convention-matching, and wrong exactly where the specification was ambiguous
7. **Record** — work item status, `tasks.md`, and the test case result

**"I ran the tests" is not verification. "I used it" is.**

### Can an agent work the ticket unattended?

On Atlassian, in principle: assign a Jira item to **Claude Agent for Jira** and it
works in a sandbox and opens a draft pull request.

**Two things to know before promising it to a client.** The app must be installed
on their Jira site — a site-admin action, and on a client-owned site their
decision, which can take weeks. And handing work to it appears to need **a person
clicking in the Jira UI**: setting the assignee through the API left the item
untouched in testing. Treat it as a possibility to confirm, not a capability to
price.

There is **no equivalent on Azure DevOps.** Those engagements are entirely
attended, which is more hands-on time for the same scope.

### While building

```
/dashboard        what moved, coverage, what needs attention
/status-report    regenerate the client-facing page
/conform          check the record against the rules
/qe               generate Gherkin from the test cases, read results back
```

Record decisions the baseline left open in `decisions.md` — what, why, what was
rejected, who decided. In week eight that is the answer to *"why is it like
this?"*, and at handoff it is what stops the client's team reverting a sensible
choice they assumed was arbitrary.

---

# Gate 4 — Handoff

```
/gate handoff
```

**Produces** the README, the runbook, and the delivery record — and walks every
requirement, marking each **met**, **descoped** with a recorded change request, or
**outstanding**.

**A requirement whose tests never ran is recorded as *unverified*, not met.**
Those are different words in an acceptance conversation, and the record uses the
true one.

---

## Checking your own work

```
/conform
```

Three outcomes, and the third is not the second:

| | |
|---|---|
| `PASS` | checked, and it holds |
| `FAIL` | checked, and it is broken |
| `skip` | **could not** be checked |

A new engagement skips nearly everything, and that is correct. Anything that
grades an empty engagement as compliant is lying to you.

**It checks:** gates signed in order, sign-off commits that exist, approved
artifacts unchanged since approval, unique identifiers, every task pointing at a
requirement that exists, every in-scope requirement covered by a test case, and
every recorded decision carrying the reason it was made.

**It cannot check** whether a requirement is the *right* requirement. An
engagement can pass every rule and still be badly run.

---

## Joining an engagement already in flight

You arrive in week four. Twenty minutes, in this order:

1. **`engagement.md`** — client, tracker, where status goes. A field reading
   `(pending)` means that thing genuinely does not exist yet
2. **`requirements.md`** — what was agreed, including what was agreed *not* to
   build
3. **`signoffs.md`** — what the client has actually approved, and at which commit.
   A gate not listed here is not agreed, however finished it looks
4. **`decisions.md`** — **why it is like this.** Read this before proposing a
   change; most "obvious improvements" are in here as rejected alternatives, with
   reasons
5. **`CLAUDE.md`** in the repository root — the conventions your code must follow

Then run `/dashboard` for what is in flight and who has it, and `/conform` for the
state you are inheriting. Better to see it on day one than to find it later and
wonder whether you caused it.

If you cannot find why something is the way it is, it was never written down. Say
so, and add it to `decisions.md` once you find out — rather than inferring a
reason from the code.

---

## Working as a team

**Task updates merge cleanly** — different rows on different branches, no
conflict. Two people *adding* a task both write `T11` and git stops, which is the
safe outcome. Resolve by renumbering, never by keeping both; if a careless
resolution slips through, `/conform` fails on the duplicate ID.

**Everyone runs their own dashboard.** "Since your last visit" is per person, so
you see what **you** missed rather than what the team missed.

**Tracker auth is per person.** Nobody inherits anyone else's access, and for
client-owned Jira the client must add each of you.

### The gates are detected, not enforced

Nothing stops someone writing a sign-off by hand and committing it. Git will
accept a fabricated approval that skips three gates without a word.

What catches it is `/conform`, after the fact — and only if something runs it.
**Put `.github/workflows/conformance.yml` in the client repository** so every pull
request touching the engagement record is checked. Without it the checks are a
thing people *can* run, which on a busy engagement means a thing nobody runs.

Treat a red conformance check as information, not a lint error to silence. `G3`
goes red the moment a signed requirement changes, and it is *supposed* to stay red
while the change order is being agreed. **Never re-sign a gate to make CI green.**

---

## The one thing to get right

**Approval is recorded against a commit.** Everything defensible here follows from
that single fact — the drift detection, the change-order conversation, the ability
to say in week five exactly what was agreed in week one and prove it.

So: never record an approval that did not happen, never re-sign a gate to make a
check go green, and never invent a SHA, a date, or an approver. A fabricated
approval is indistinguishable from a real one at a glance, which is precisely what
makes it worse than no record at all.
