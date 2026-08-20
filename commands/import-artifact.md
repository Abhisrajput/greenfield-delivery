---
description: Bring a document you already have into the engagement as a gate artifact
argument-hint: <gate> <path to the existing document>
---

# Import artifact

Most engagements do not start empty. There is an SOW, a requirements document
from the client, a design someone wrote before you arrived. This command brings
one in as a gate artifact instead of pretending the gate produced it.

## 1. Check the inputs

You need a gate and a path. **If either is missing, stop and ask** — do not
guess which gate a document belongs to from its filename, and do not search the
repository for something that looks close.

| Gate | Becomes |
|---|---|
| `discovery` | `docs/engagement/discovery.md` |
| `requirements` | `docs/engagement/requirements.md` |
| `design` | `docs/engagement/design.md` |

`build` and `handoff` produce working software and a handover record; there is
nothing to import. **If asked for either, stop and say so.**

Read `docs/engagement/engagement.md` first. If it does not exist, stop — run
`/new-engagement` before importing anything.

**If the target already exists, stop and say so.** Show what is there and ask
whether to replace it. Silently overwriting an artifact that may already carry
a sign-off destroys the record that made it defensible.

## 1a. The source can be a Confluence page

Clients keep requirements in Confluence more often than in a file, and the
Atlassian MCP server this plugin declares can read one directly — pass the page
URL or its ID instead of a path.

**Record where it came from, and at which version.** A Confluence page reports
a `version.number`, which is the same kind of fact as a commit SHA: it pins
*which* text you read. Put it at the top of the imported artifact:

```markdown
Imported from Confluence page 360453 "Order Intake — Requirements", version 7,
read on 2026-08-20.
```

Without the version, "imported from the Confluence page" names a document that
has since changed and cannot be recovered.

### After the import, `requirements.md` is the baseline — not the page

This is the part to say out loud to the client, because otherwise you have two
specifications and no way to tell which one was agreed.

The page will keep moving. Somebody will edit it next week, and **nothing will
tell you** — `/conform` checks the engagement record against git, and it cannot
see across into Confluence. The sign-off is recorded against the commit of
`requirements.md`, so that is what the client approved.

Say so at import: *"I have taken version 7 into the engagement record. From
here the record is what we build and sign against; if the page changes, tell me
and we will treat it as a change request."*

**Do not re-import silently later.** A second import overwrites a signed
baseline with text nobody approved. If the page has moved, that is an amendment
— see `requirements-gate`.

## 1b. Is it a document, or a transcript?

They need different handling, and treating the second as the first is how
invented requirements get into a signed baseline.

| | A document | A transcript, notes, an email thread |
|---|---|---|
| Shape | Already asserts requirements | Contains decisions, half-decisions, and thinking aloud |
| Job | Convert structure, keep wording | **Extract candidates, confirm each** |
| Output | Rows in `## Functional` | Rows in `## Open questions`, with the quote |

**If the source is a transcript, stop and say so** before writing anything into
`## Functional`. Then follow the extraction rules in `requirements-gate`: every
candidate carries the words that produced it, and nothing acquires an
acceptance criterion the client did not say.

A transcript can absolutely be imported. It just cannot be imported as though
somebody had already agreed to it.

## 2. Read the document as it is

Read the source file. **Do not rewrite it yet.** Report what it contains
against the standard for that gate, using the gate's own skill —
`requirements-gate` for requirements, `architecture-design` for design,
`discovery` for discovery.

Say plainly which parts of the standard it already meets and which it does not.
For requirements this usually means:

- requirements with no acceptance criterion, or criteria that cannot be tested
- compound requirements that need splitting before they can be accepted
- no stated non-goals, so scope has no edge
- identifiers absent or not unique

**Do not fix these silently.** The gaps are the value of this step: they are
what the client's existing document does not yet commit to, and they are
cheaper to raise now than at acceptance.

## 3. Convert only the structure

Rewrite the document into the canonical format for that artifact — the tables
and section headings `greenfield-delivery` defines — **preserving the author's
content and wording**. Renumber nothing that already carries an identifier the
client uses; if the source has its own IDs, keep them.

Where the source says something untestable, keep it and mark it. Write the
criterion cell as the source's own words, and list the requirement in your
report as needing a testable criterion. **Never invent an acceptance criterion
the client did not agree to** — a criterion you wrote yourself reads exactly
like one they approved, and only one of those is defensible.

Where the source is silent, leave the cell empty rather than filling it. An
empty criterion fails `R3` in `/conform`, which is the correct and visible
outcome.

## 4. Record where it came from

Add a line at the top of the artifact naming the source document, its date, and
who provided it. The engagement record must show that this artifact was
imported rather than produced here — six weeks later nobody remembers, and the
provenance changes what the sign-off means.

## 5. Stop before sign-off

**Importing is not approving.** Do not add a row to `signoffs.md`.

An imported document has not been through its gate. Say what remains:

> `requirements.md` is imported and in canonical form. Four requirements have
> no testable acceptance criterion (R2, R5, R7, R9), and there are no stated
> non-goals. Run `/gate requirements` to close those gaps and take it to the
> client for sign-off.

If the client already approved the source document out of band, that approval
can be recorded — but it is recorded against **this** commit, with the evidence
link, by `/gate`. Say so, and let `/gate` do it.

## 6. Check it

Run `/conform`. Report the result honestly, including any rule that could not
be checked.
