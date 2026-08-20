---
name: tracker-azure-devops
description: Use when the engagement tracker is Azure DevOps - creating epics, features, or product backlog items, updating states, or writing ADO Wiki status pages.
---

# Tracker: Azure DevOps

Applies when `engagement.md` declares `tracker.type: azure-devops`. General item
standards are in `tracker-conventions`.

## Status of this skill

**Nothing in here has been run against a live Azure DevOps organization.**

That is not the same as invented, and the difference matters when you are
deciding whether to trust it:

| | |
|---|---|
| **Sourced from Microsoft** | that the remote MCP server cannot authenticate from Claude Code, and that Azure Boards' work-item-to-PR automation runs on a different vendor's agent. Quoted, not inferred. |
| **Sourced from the package** | the local server's name and that it takes the organization as a required argument. |
| **Never executed** | every procedure below — the `.mcp.json` shape, item creation, the hierarchy mapping, state handling, the wiki write. |

Run the pre-flight below before committing an engagement to this path. **You
are the first**, and finding a problem during a client's build phase is far
worse than finding it in twenty minutes on a scratch project.

If something here is wrong, the fix belongs in this file so the next
engagement does not rediscover it.

## Pre-flight — twenty minutes, before you promise anything

Do this on a scratch ADO project, not the client's:

1. **Node and the server.** `npx -y @azure-devops/mcp <org>` starts, and the
   first tool call opens a browser login. If it hangs with no browser, stop —
   that is the failure mode to report, not to work around.
2. **Read before you write.** List projects, then read one existing work item.
   Connected is not the same as *able to reach the client's project*.
3. **Find the process template.** Basic, Agile, Scrum and CMMI have **different
   work item types and different state names** — Agile has User Story, Scrum
   has Product Backlog Item. Everything below depends on which one the client
   uses, and it cannot be guessed.
4. **Read the states for one work item type**, and write them down. Do not
   assume `To Do / Doing / Done`.
5. **Create one item, then delete it.** Confirms write access and the field
   shape before an engagement depends on it.

Record what you find in the client's `engagement.md` under `## Tracker`. The
next person on the engagement should not have to repeat this.

## Configuration

Read from `engagement.md`:

```markdown
## Tracker
- type: azure-devops
- org: https://dev.azure.com/acme
- project: ACME
- epic: 4821
```

**Always scope to this organization and project.** The MCP server reaches every
organization the authenticated account can access.

## Hierarchy

| Level | Maps to |
|---|---|
| Epic | The engagement |
| Feature | A requirement group |
| Product Backlog Item / User Story | One requirement (`R<n>`) |
| Task | A unit of work |

The exact hierarchy depends on the client's process template (Agile, Scrum, or
CMMI). **Check the template before creating items** — Scrum uses Product
Backlog Item where Agile uses User Story, and states differ between them.

## No unattended tier

> ⚠️ **There is no Claude Agent for Azure DevOps.**
>
> Azure Boards' work-item-to-pull-request automation runs on GitHub Copilot
> custom agents — a different vendor's agent, which this methodology does not
> plug into.
>
> **The build phase on an ADO engagement is entirely attended.** Work items are
> worked by hand in Claude Code.

### The margin consequence

An ADO engagement consumes more hands-on time than an equivalent Atlassian
one. If it was priced identically, it carries worse margin.

This must be handled at **Discovery**, not discovered mid-build. If an ADO
engagement is already underway and was priced on Atlassian assumptions, raise
it now rather than absorbing it.

Do not attempt to close the gap by building a webhook-to-headless bridge. That
is a service, and services are excluded by design.

## Mapping states to `tasks.md`

`tasks.md` takes exactly `todo`, `in-progress`, `blocked`, `done`, `dropped`.
Azure DevOps state *names* vary by process template, so **matching on the name
does not survive a change of template** — the same lesson Jira taught, where
the default workflow's "In Review" matches none of the five.

**Map on the state category, not the state name.** ADO groups every state into
a category regardless of template, and that grouping is the stable thing:

| ADO state category | `tasks.md` |
|---|---|
| Proposed | `todo` |
| In Progress | `in-progress` |
| Resolved | `in-progress` — resolved is not delivered |
| Completed | `done` |
| Removed | see below |

**Confirm the category names on the client's project before relying on this
table** — it is written from documentation, not from a run. If what you find
differs, correct it here.

`blocked` and `dropped` are local, exactly as on Jira. A blocked item usually
sits in an ordinary in-progress state and ADO has no way to say otherwise, so
**a pull must never overwrite a local `blocked` or `dropped`** — that would
erase the two states most worth reporting. ADO's `Removed` is the closest thing
to `dropped`, but confirm the client uses it that way before treating them as
equivalent.

## Wiki

The business-user status page lives in the ADO Wiki:

```markdown
## Progress reporting
- narrative: ado-wiki
- wiki: ACME.wiki
- page: /Delivery Status
```

ADO Wiki is markdown backed by a git repository, so generating the page is
simpler than Confluence — it is a markdown commit rather than a page API call.
Content standard is in `progress-reporting`.

## Dashboard

Configure an ADO Dashboard for the live picture — burndown, in flight, blocked.
Always current, no command to run, and it is what business users should be sent
for day-to-day status.

## MCP setup — local server, per engagement

The official server is `microsoft/azure-devops-mcp`, maintained by the Azure
DevOps product team (MIT). It covers work items, repos, pipelines, wiki, and
test plans.

### Use the local server. The remote one cannot work here.

Microsoft hosts a remote server at `https://mcp.dev.azure.com/{org}` and
recommends it generally — but **it does not work with Claude Code**, and this
is documented by Microsoft, not a limitation we discovered:

> Claude Desktop, Claude Code, Cursor, and Codex don't currently support the
> Microsoft Entra authentication flow required by the remote Azure DevOps MCP
> Server. Use the local MCP Server with these clients.

The cause is structural: those clients need dynamic OAuth client registration,
and Microsoft Entra ID does not support that flow. It is not a version issue
and not something to retry. **Do not attempt to configure the remote endpoint** —
it will fail at authentication, after appearing to be configured correctly.

Re-check this only if Entra adds dynamic client registration.

### Config goes in the client project, not this plugin

The local server takes the **organization as a required positional argument**,
and the organization differs per client. So it cannot live in this plugin's
`.mcp.json` — it is written per engagement.

`/new-engagement` writes this into the client repository's `.mcp.json` when the
tracker is Azure DevOps:

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

`<organization>` is the org short name — for `https://dev.azure.com/acme`, that
is `acme`, not the full URL.

Optionally set defaults to skip selection prompts:

```json
      "env": {
        "ado_mcp_project": "ACME",
        "ado_mcp_team": "ACME Team"
      }
```

### Per-machine prerequisites

- **Node.js 20+** with `npx` available
- **A browser login on first tool use.** The server opens a browser for
  Microsoft account authentication the first time an ADO tool runs. This is
  interactive — expect it, and do not treat the pause as a hang.
- Membership in the client's Azure DevOps organization and project

This is install-once setup, not ongoing maintenance, which is why it is
acceptable under the firm's constraints. But it is friction an Atlassian
engagement does not have — one more reason Atlassian is the recommended
default where the client has no preference.
