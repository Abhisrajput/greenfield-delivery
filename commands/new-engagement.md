---
description: Start a new client engagement - scaffold the docs, capture tracker and reporting config
argument-hint: Optional client name
---

# New Engagement

Set up a new greenfield client engagement. Use the `greenfield-delivery` skill
for the gate sequence.

## 1. Interview

Ask for what you cannot infer. **One question at a time** — this is a
conversation with someone mid-setup, not a form.

Required:

- Client name
- Engagement shape (fixed scope + duration, time and materials, other)
- Primary client contact
- Shared Slack channel
- **Tracker**: Jira or Azure DevOps, plus site/org and project key
- Repository URL, if it exists yet

Then determine the narrative reporting surface, in this order:

1. Atlassian client → does the client have **Confluence**? If yes, `confluence`
   with the space key. Jira without Confluence is common — ask, do not assume.
2. Azure DevOps client → `ado-wiki` with the wiki name.
3. Neither → `repo-markdown`.

**Decide this once, here.** Deciding per report produces inconsistent
locations, and business users lose track of where status lives.

## 2. Flag the Azure DevOps margin implication

If the tracker is Azure DevOps, say so explicitly and once:

> This engagement is on Azure DevOps, so there is no unattended tier — the
> build phase is entirely attended. That is more hands-on time than an
> equivalent Atlassian engagement. Worth confirming it was priced that way.

Do not repeat it later; state it once, clearly, at setup.

## 3. Scaffold

Create in the project repository:

```
docs/engagement/
├── engagement.md
├── requirements.md    # skeleton with empty tables
├── design.md          # skeleton
├── tasks.md           # title + header row, no task rows
├── signoffs.md        # empty table with headers
└── decisions.md       # empty table with headers
```

Add `discovery.md` if the engagement includes a Discovery gate.

`decisions.md` is the working-decision log. Scaffold it on a team
engagement; on a solo one it is optional and an empty file nobody fills
in is worse than none. Ask.

Use the canonical formats in the `greenfield-delivery` skill for
`engagement.md` and `signoffs.md`, and the output shape in `requirements-gate`
for the `requirements.md` skeleton. Do not invent these — other skills read
them by exact block and column name.

## 4. Write `engagement.md`

Follow the canonical format in the `greenfield-delivery` skill. It must contain
the `## Tracker`, `## Progress reporting`, and `## Repository` blocks — every
other skill reads them, and a missing tracker block means an agent can act
against the wrong client's project.

## 5. Azure DevOps only — write the project `.mcp.json`

Skip this for Atlassian engagements; the Atlassian server is configured at
plugin level.

The Azure DevOps MCP server takes the organization as a required argument, so
it cannot be configured plugin-wide. Write it into the **client repository's**
`.mcp.json`:

```json
{
  "mcpServers": {
    "azure-devops": {
      "command": "npx",
      "args": ["-y", "@azure-devops/mcp", "<organization>"]
    }
  }
}
```

`<organization>` is the short name — for `https://dev.azure.com/acme`, that is
`acme`.

If the repository already has an `.mcp.json`, merge into it rather than
overwriting.

Then say what is needed locally, once:

> Azure DevOps needs Node.js 20+ and a one-time browser login the first time an
> ADO tool runs. If Claude seems to pause on the first tracker call, that's the
> login window.

**Do not configure the remote ADO endpoint** (`mcp.dev.azure.com`). Microsoft
documents that it cannot authenticate from Claude Code. See
`tracker-azure-devops`.

## 6. Report

Confirm what was created, which tracker and reporting surface were recorded,
and name the next step: gate 1 via `/gate requirements` (or `/gate discovery`
if Discovery is in scope).
