---
name: tracker-jira
description: Use when the engagement tracker is Jira - creating epics, stories, or issues, updating status, writing Confluence status pages, or assigning work to Claude Agent for Jira.
---

# Tracker: Jira (Atlassian)

Applies when `engagement.md` declares `tracker.type: jira`. General item
standards are in `tracker-conventions`.

## Configuration

Read from `engagement.md`:

```markdown
## Tracker
- type: jira
- site: acme.atlassian.net
- project: ACME
- epic: ACME-142
```

**Always scope to this site and project.** The Atlassian MCP server reaches
every site the authenticated account can access, so an unscoped call can act
against a different client's project. Never infer the site from context.

## Hierarchy

| Level | Maps to |
|---|---|
| Epic | The engagement |
| Story | One requirement (`R<n>`) |
| Sub-task | A unit of work under a story |

## Creating the structure

At gate 1, after requirements are approved: create the epic, then one story per
requirement. Put the requirement number at the start of the story summary so it
is visible in list views — `R7 — Order list renders within 2s at 10k orders`.

At gate 2, after design is approved: break stories into sub-tasks from
`tasks.md`, carrying acceptance criteria across verbatim.

## Unattended work — Claude Agent for Jira

Atlassian engagements have an unattended tier — **once the Claude app is
installed on the client's Jira site.** It is not there by default, and the
methodology cannot install it: it is a site-admin action in Atlassian
Marketplace, and on a client-owned site that is the client's decision.

**Check before promising it.** Search the site's assignable users for
`Claude`. It registers as an **app** account named `Claude Agent for Jira`, not
as a person. No match means the app is not installed, and every instruction
below is unavailable — the assignee dropdown simply will not contain it.

**A fresh install takes a few minutes to become searchable.** Immediately after
installing, that search returns nothing; the account appears shortly
afterwards. So a single empty result right after an install is not proof it
failed — wait and search again before telling anyone it is unavailable, or the
check reports the opposite of the truth.

Say so plainly rather than planning around a tier that does not exist:

> The Claude app is not installed on this Jira site, so there is no unattended
> tier here. The build phase is entirely attended unless the client installs
> it. That is the same position as an Azure DevOps engagement, and worth
> pricing the same way.

**Do not assign work to an agent account you have not confirmed exists.** An
item assigned to nobody looks identical to an item waiting on an agent, and the
work silently does not happen.

### Handing work over is a UI action, not an API one

Assigning the agent **through the REST API did not start it.** On a live test
the assignee was set correctly — the field showed `Claude Agent for Jira`,
account type `app`, active — and after several minutes the item was still
`To Do` with no comment, no branch and no pull request.

Mentioning it through the API did not start it either. The mention was stored
as `data-id="id-0"` rather than the agent's account ID, so it bound to nobody.

**Plan for a person clicking.** Assigning through the dropdown in the Jira UI
is the path that works, and `/sync-tracker` cannot do it for you. An
engagement that expects to feed the unattended tier programmatically should
budget that handover as a manual step, or build a Jira automation rule to do
the assigning — a rule runs inside Jira and fires the events the app listens
for.

This is worth knowing before promising a client that work flows from
`tasks.md` to a working agent without anyone touching Jira. It does not, today.

Once installed, an item can be assigned to Claude directly:

- Select **Claude** in the assignee dropdown, or
- Mention the agent in a comment, or
- Configure a Jira automation rule to auto-assign matching items

Claude reads the item context, works in a managed sandbox, and opens a **draft
pull request**.

### Before assigning

Run the readiness checklist in `tracker-conventions`. Then confirm the
repository has a current `CLAUDE.md` — the agent is a generic implementer and
`CLAUDE.md` is the only thing making its output conform to the firm's standard
and the client's agreed design.

**An engagement with a thin `CLAUDE.md` should not use the unattended tier.**
Generic output reviewed by a human is slower than a human writing it.

### What stays attended

Anything failing the readiness checklist, plus anything architectural,
security-related, or requiring a client conversation.

## Confluence

Confluence is both an **output** surface (the status page `/status-report`
writes) and an **input** one — clients keep requirements, briefs and meeting
notes there far more often than in a file.

Reading it needs the `read:page:confluence` scope, which the consent screen
grants alongside Jira **only if Confluence exists on the site at the time you
authorize**. Add Confluence to a site after authorizing and the existing token
does not gain access: the API answers `403 The app is not installed on this
instance` rather than anything mentioning scopes. Re-authorize; retrying does
nothing.

To import a page as a gate artifact, see `/import-artifact` — it takes a page
URL or ID, and records the page's `version.number` so the import names an exact
text rather than a moving one.


The business-user status page lives in Confluence when available. Config:

```markdown
## Progress reporting
- narrative: confluence
- space: ACME
- page: Delivery Status
```

The Atlassian MCP server writes pages as well as issues, so `/status-report`
needs no additional integration. Content standard is in `progress-reporting`.

If the client has Jira but not Confluence — common — the narrative falls back
to `docs/engagement/status.md` in the repository. Record the fallback in
`engagement.md` once, at `/new-engagement`, rather than deciding per report.

## Dashboard

Configure a Jira dashboard or use the roadmap view for the live picture. This
is the half of progress reporting that needs no command run — it is always
current, and it is what business users should be sent for day-to-day status.

## MCP setup — hosted server, configured once

Unlike Azure DevOps, the Atlassian server is **remote and already declared in
this plugin's `.mcp.json`**:

```json
{
  "mcpServers": {
    "atlassian": {
      "type": "http",
      "url": "https://mcp.atlassian.com/v1/mcp/authv2"
    }
  }
}
```

Nothing goes in the client project. The endpoint is the same for every
Atlassian site, because the *site* comes from your authorization rather than
from the URL — which is why this can live plugin-wide while the ADO server
cannot (it takes the organization as a required argument).

The older `/v1/sse` endpoint was retired on 2026-06-30. If you find it in an
old config, replace it; it will not fail loudly, it will simply never connect.

### Authorize, once per person per machine

Auth is OAuth 2.1 with Dynamic Client Registration, so **there is no app to
create in Atlassian admin** and nothing for the client's administrator to
approve in advance. The client self-registers on first connect.

1. Run `/mcp` in Claude Code. The `atlassian` server appears, unauthenticated.
2. Start authentication for it. A browser opens on Atlassian's consent screen.
3. Approve. The browser hands back a code and the session completes.

**If the consent screen says "Supported sites required", stop — there is
nothing wrong with the setup.** The screen reads:

> Your account isn't currently associated with a supported site.

with *0 out of 0 permissions selected* and **Accept** greyed out. It means the
Atlassian account you are signed in as has no Jira or Confluence site attached
at all, so there is nothing to grant access to. This fails one step *earlier*
than the failures in the table below, which all assume authorization completed.

Two causes, and they need different actions:

- **You are signed into the wrong Atlassian account** — a personal one rather
  than the one on the client's site. Sign out at `id.atlassian.com` and retry.
- **You genuinely have no site yet.** Create a free Jira Cloud site at
  `atlassian.com/software/jira` — it takes a couple of minutes and is enough
  for a scratch engagement. The client's own site still requires them to invite
  you.

Retrying authorization changes nothing until one of those is true.

The token is held per person on that machine. It is not shared, not committed,
and not part of the engagement — a second person on the same engagement
authorizes separately, and so does the same person on a second machine.

### Verify before you rely on it

**Do not assume the connection works because `/mcp` shows it connected.**
Connected means the token was accepted, not that you can reach the client's
project. Ask for the accessible resources, then read one known issue from the
engagement's project.

If authorization completed but the read fails, the failure is almost always one
of three things, and they need different people to fix them:

| Symptom | Cause | Who fixes it |
|---|---|---|
| No sites listed at all | Authorized with the wrong account — a personal Atlassian login rather than the one on the client's site | You. Re-authorize. |
| Site listed, project not found | You are on the site but not in the project, or the project key in `engagement.md` is wrong | Check `engagement.md` first, then the client |
| Site not listed | You are not a member of the client's Atlassian site | The client. They must invite you. |

**Say which of these it is rather than retrying.** Each person reaches only
sites they belong to, so for client-owned Jira there is no configuration that
substitutes for the client adding you.

### What to do while access is pending

Getting added to a client's Atlassian site routinely takes days. That blocks
`/sync-tracker`, and nothing else.

Do not let it block the engagement, and **do not invent issue keys to proceed**.
`tasks.md` carries `(pending)` in the `Item` column until the tracker returns a
real key; that is what the placeholder is for. Discovery, requirements and
design all run to completion without a tracker, and `/sync-tracker` fills the
column in one pass when access arrives.
