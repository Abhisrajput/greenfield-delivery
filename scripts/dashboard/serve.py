"""HTTP layer and state assembly. Read-only: GET is the only method served."""

from __future__ import annotations

import hashlib
import difflib
import json
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import analyse, events, history, render
from .model import Drift, Feed, Gate, State
from .parse import parse_engagement, parse_requirements, parse_signoffs, parse_tasks

ENGAGEMENT_DIR = Path("docs") / "engagement"
TASKS_REL = str(ENGAGEMENT_DIR / "tasks.md")
PORT_RANGE = range(8420, 8430)
GATE_SEQUENCE = (
    ("Discovery", "discovery.md"),
    ("Requirements", "requirements.md"),
    ("Design", "design.md"),
    ("Build", "tasks.md"),
    ("Handoff", "README.md"),
)
DEFAULT_CADENCE_DAYS = 7


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def gates_from(signoffs, signoff_status: dict) -> tuple[Gate, ...]:
    """Every gate always appears. A gate whose artifact changed after approval,
    or whose commit cannot be found, is never shown as approved.

    `signoff_status` is keyed by `(commit, artifact)`, not commit alone: one
    commit can legitimately cover several artifacts (a gate that commits
    several files together, each signed off in its own row at the same SHA),
    so a commit-only key would let one artifact's verified status stand in
    for another's."""
    recorded = {s.gate.lower(): s for s in signoffs.signoffs}
    gates: list[Gate] = []
    last_approved = -1

    for index, (name, artifact) in enumerate(GATE_SEQUENCE):
        signoff = recorded.get(name.lower())
        if signoff is None:
            gates.append(Gate(name, artifact, "pending", "", ""))
            continue
        state = signoff_status.get((signoff.commit, signoff.artifact), "unverifiable")
        if state == "unchanged":
            gates.append(Gate(name, artifact, "approved", signoff.date, signoff.commit))
            last_approved = index
        elif state == "changed":
            # Distinct from "unverifiable". The commit IS in the repository and
            # the artifact moved since it. Collapsing the two made the rail
            # announce "commit <sha> is not in this repository" about a commit
            # sitting in the log — sending the reader to look for something
            # that was never missing, and hiding the scope drift that had
            # actually happened. Neither is approved; they are different facts.
            gates.append(Gate(name, artifact, "changed", signoff.date, signoff.commit))
        else:
            gates.append(Gate(name, artifact, "unverifiable", signoff.date, signoff.commit))

    if last_approved + 1 < len(gates):
        nxt = gates[last_approved + 1]
        if nxt.state == "pending":
            gates[last_approved + 1] = Gate(nxt.name, nxt.artifact, "current", "", "")
    return tuple(gates)


def _status_age_days(root: Path, narrative: str) -> int | None:
    """None means the status page is not visible locally — not that it is fresh."""
    if narrative != "repo-markdown":
        return None
    path = root / ENGAGEMENT_DIR / "status.md"
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    return int(age // 86400)


def _resolve_artifact_status(root: Path, commit: str, artifact: str) -> str:
    """The `Artifact` column names a file that may live in `docs/engagement/`
    (discovery, requirements, design, tasks) or at the repository root (the
    Handoff README). Try both documented locations, in order, at the approved
    commit, and use the first that resolves to something other than
    "unverifiable". If neither location held the file at that commit, the
    engagement-relative result — which `artifact_status` guarantees is
    "unverifiable" in that case — is what gets returned.
    """
    engagement_relative = str(ENGAGEMENT_DIR / artifact)
    status = history.artifact_status(root, commit, engagement_relative)
    if status != "unverifiable":
        return status

    repo_root_relative = artifact
    status = history.artifact_status(root, commit, repo_root_relative)
    if status != "unverifiable":
        return status

    return "unverifiable"


FEED_CAP = 200
_FEED_LOCK = threading.Lock()
_feed_cache: dict = {}

_WATCHED = {
    "docs/engagement/tasks.md": ("tasks", parse_tasks),
    "docs/engagement/requirements.md": ("reqs", parse_requirements),
    "docs/engagement/signoffs.md": ("signoffs", parse_signoffs),
    "docs/engagement/engagement.md": ("engagement", parse_engagement),
}

# Order is semantic, not cosmetic. requirements.md must be diffed BEFORE
# signoffs.md is absorbed into `signed`: a sign-off approves requirements.md
# as at that commit, so a criterion change in the SAME commit is part of what
# was approved and must not be reported as drift against it. Git's
# `--name-only` output happens to sort alphabetically, which today puts
# requirements.md before signoffs.md, but that is an accident of git's
# ordering, not a guarantee this code can rely on — so the order is pinned
# here instead.
_PROCESS_ORDER = (
    "docs/engagement/requirements.md",
    "docs/engagement/tasks.md",
    "docs/engagement/engagement.md",
    "docs/engagement/signoffs.md",
)


def _in_process_order(paths):
    """`paths` sorted to `_PROCESS_ORDER`; any watched path not listed there
    (none exist today) sorts after all listed ones rather than raising, so an
    unlisted watched file degrades to "processed last" instead of crashing."""
    rank = {path: index for index, path in enumerate(_PROCESS_ORDER)}
    return sorted(paths, key=lambda p: rank.get(p, len(_PROCESS_ORDER)))


def build_feed(root: Path, *, cap: int = FEED_CAP) -> Feed:
    """Walk the engagement's history once and extract every event.

    A commit whose files will not parse contributes no events and is counted.
    A feed that silently drops a commit looks like a quiet day, and a quiet
    day is what someone would repeat to a client.

    Three things can go wrong with one watched file at one commit, and all
    three end the same way — no events from that file, and the commit counted
    towards `feed.unreadable`, so the footnote never claims more than was read:

    - **git could not be read** (`history.file_at` returns `ok=False`).
    - **the file was deleted** (`ok=True, content=None` where the previous
      version was present). A real change, not a quiet day.
    - **the file parsed only in part** (`_unparsed`): the header was found but
      rows went into `problems`.

    In every one of the three, `previous[name]` is left at the last known-good
    version rather than advanced. That is the single rule holding the seam
    together: a baseline we do not trust makes the NEXT commit fabricate — an
    absent baseline turns everything already there into fresh `added` events,
    and a partially-parsed one turns a dropped row into a removal and its
    return into an addition.
    """
    ok, commits = history.engagement_commits(root)
    if not ok:
        return Feed((), 0, 0, False, 0)

    previous: dict = {name: None for name, _ in _WATCHED.values()}
    signed: set = set()
    collected: list = []
    unreadable = 0

    for sha, when, paths in commits:
        commit_failed = False
        for path in _in_process_order(paths):
            entry = _WATCHED.get(path)
            if entry is None:
                continue
            name, parser = entry
            file_ok, content = history.file_at(root, sha, path)
            if not file_ok:
                commit_failed = True
                continue
            current = parser(content)
            was = previous[name]
            if was is not None and was.present and not current.present:
                # The file was deleted in this commit. `git rm` of tasks.md is
                # real activity — losing it makes the busiest week on the
                # engagement read as a quiet one.
                #
                # It is counted rather than emitted because the spec fixes the
                # event vocabulary at eight kinds, and none of them states "the
                # file is gone": `task.dropped` would assert every task was cut
                # from scope, which is a commercial claim no one made. The
                # footnote's "N could not be read, so events may be missing" is
                # literally true here and claims nothing further.
                #
                # `previous[name]` is deliberately NOT advanced to the absent
                # version. Doing that is what made the restoring commit bail on
                # `not previous.present` and swallow every change made while the
                # file was away; leaving the last known-good version in place
                # means the restore diffs against it and the real transitions
                # surface.
                commit_failed = True
                continue
            if _unparsed(current):
                # Counted unconditionally, and checked before the extractors
                # rather than only when they happen to return nothing: a commit
                # can yield real events from one watched file while another
                # dropped rows on the floor, and the earlier `if not produced`
                # let exactly those commits report as fully read.
                #
                # `previous[name]` is left at the last known-good version for
                # the same reason as the deletion branch above. Making a
                # partially-parsed version the baseline is what turns one typo
                # into two wrong events: the dropped row reads as a removal
                # now, and its return reads as an addition next commit.
                commit_failed = True
                continue
            if name == "tasks":
                produced = events.from_tasks(was, current, when, sha)
            elif name == "reqs":
                produced = events.from_requirements(
                    was, current, when, sha, frozenset(signed)
                )
            elif name == "signoffs":
                produced = events.from_signoffs(was, current, when, sha)
            else:
                produced = events.from_engagement(was, current, when, sha)
            collected.extend(produced)
            if name == "signoffs" and events.readable(current):
                signed.update(s.artifact for s in current.signoffs)
            previous[name] = current
        if commit_failed:
            unreadable += 1

    collected.sort(key=lambda e: (e.when, e.commit), reverse=True)
    truncated = max(0, len(collected) - cap)
    return Feed(tuple(collected[:cap]), len(commits), unreadable, True, truncated)


def _unparsed(parsed) -> bool:
    """Did this commit's version of a watched file fail to parse, in whole or
    in part?

    The negation of `events.readable`, and deliberately the same predicate:
    `_unparsed` is the sole input to `feed.unreadable`, so any version the
    event extractors refuse to diff must be a version the footnote admits to.
    When the two disagree the dashboard goes quiet and simultaneously asserts
    it read everything — the exact shape of failure this panel exists to
    prevent.

    An absent file is not unparsed: `build_feed` handles deletion separately,
    because "the file is gone" is a different fact from "the file is
    unreadable" and only the caller knows whether it was there before.
    """
    return parsed.present and not events.readable(parsed)


def cached_feed(root: Path) -> Feed:
    """Events come from commits, so they change only when HEAD does. Keyed on
    HEAD alone, separately from State: editing a file without committing must
    not re-walk history, which is the most expensive thing this product
    does."""
    key = (root, history.head(root))
    with _FEED_LOCK:
        entry = _feed_cache.get(root)
        if entry is None or entry[0] != key:
            entry = (key, build_feed(root))
            _feed_cache[root] = entry
        return entry[1]


def _days_since(iso_date: str) -> int | None:
    """None means cannot tell. A missing or unparseable date has no measurable
    age, and rendering 0 would assert something we do not know."""
    try:
        then = datetime.fromisoformat(iso_date)
    except (ValueError, TypeError):
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - then).days)


def _days_in_gate(gates) -> int | None:
    approved = [g for g in gates if g.state == "approved" and g.date]
    if not approved:
        return None
    return _days_since(approved[-1].date)


def _days_since_commit(root: Path) -> int | None:
    result = history._run(root, "log", "-1", "--format=%cI")
    if result is None or result.returncode != 0:
        return None
    return _days_since(result.stdout.strip())


def build_state(root: Path) -> State:
    base = root / ENGAGEMENT_DIR
    engagement = parse_engagement(_read(base / "engagement.md"))
    reqs = parse_requirements(_read(base / "requirements.md"))
    tasks = parse_tasks(_read(base / "tasks.md"))
    signoffs = parse_signoffs(_read(base / "signoffs.md"))

    is_repo = history.is_repo(root)
    signoff_status = {
        (s.commit, s.artifact): (
            _resolve_artifact_status(root, s.commit, s.artifact)
            if is_repo
            else "unverifiable"
        )
        for s in signoffs.signoffs
    }

    narrative = engagement.engagement.narrative if engagement.engagement else ""
    history_ok, task_revisions = history.revisions(root, TASKS_REL) if is_repo else (True, ())
    trend = analyse.trend(history_ok, task_revisions)

    found = analyse.findings(
        engagement=engagement,
        reqs=reqs,
        tasks=tasks,
        signoffs=signoffs,
        signoff_status=signoff_status,
        status_age_days=_status_age_days(root, narrative),
        cadence_days=DEFAULT_CADENCE_DAYS,
    )

    gates = gates_from(signoffs, signoff_status)
    days_in_gate = _days_in_gate(gates)
    days_since_commit = _days_since_commit(root)

    return State(
        engagement=engagement,
        reqs=reqs,
        tasks=tasks,
        signoffs=signoffs,
        signoff_status=signoff_status,
        findings=found,
        trend=trend,
        gates=gates,
        is_repo=is_repo,
        feed=cached_feed(root),
        days_in_gate=days_in_gate,
        days_since_commit=days_since_commit,
        drift=build_drift(root, signoffs, signoff_status),
    )


# A rewritten requirements.md can produce hundreds of diff lines, and a panel
# that dumps them is one nobody reads. Enough to see WHAT moved; git is there
# for the rest.
DRIFT_CAP = 40


def build_drift(root: Path, signoffs, signoff_status: dict) -> tuple:
    """What changed in each artifact whose approval no longer covers it.

    Only for the sign-off that currently counts per gate — a superseded row
    describes a change the client has since re-approved, and showing it as
    live drift would repeat the contradiction `current_signoffs` exists to
    stop.
    """
    out = []
    for signoff in analyse.current_signoffs(signoffs):
        if signoff_status.get((signoff.commit, signoff.artifact)) != "changed":
            continue
        relpath = _artifact_path(root, signoff.artifact)
        ok_then, then = history.file_at(root, signoff.commit, relpath)
        try:
            nowtext = (root / relpath).read_text(encoding="utf-8")
        except OSError:
            ok_then, nowtext = False, None
        if not ok_then or then is None or nowtext is None:
            out.append(Drift(signoff.artifact, signoff.commit, None, 0,
                             "the approved version could not be read"))
            continue
        lines = tuple(difflib.unified_diff(
            then.splitlines(), nowtext.splitlines(),
            fromfile=f"approved at {signoff.commit}", tofile="now", lineterm="", n=1,
        ))
        truncated = max(0, len(lines) - DRIFT_CAP)
        out.append(Drift(signoff.artifact, signoff.commit,
                         lines[:DRIFT_CAP], truncated))
    return tuple(out)


def _artifact_path(root: Path, artifact: str) -> str:
    """`signoffs.md` names artifacts by filename. Resolve the same two places
    `_resolve_artifact_status` does, and in the same order."""
    engagement_relative = f"{ENGAGEMENT_DIR}/{artifact}"
    if (root / engagement_relative).exists():
        return engagement_relative
    return artifact


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def slugs(roots) -> tuple:
    """Stable, URL-safe identifiers for the engagement roots, in the order
    given.

    A directory name that yields nothing usable falls back to its position, so
    every root is always addressable — a root with no reachable URL would be
    invisible in the portfolio, which is the failure this whole view exists to
    avoid.
    """
    out = []
    seen: dict = {}
    for index, root in enumerate(roots, 1):
        base = _slugify(Path(root).name) or f"engagement-{index}"
        count = seen.get(base, 0) + 1
        seen[base] = count
        out.append((base if count == 1 else f"{base}-{count}", Path(root)))
    return tuple(out)


_CACHE_LOCK = threading.Lock()
# Keyed by root, not a single slot: with several engagements a one-slot cache
# would evict on every alternating request, so each poll would rebuild the
# other engagement from scratch — the repeated-subprocess cost returning by a
# different route.
_cache: dict = {}


def _mtime(path: Path):
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _cache_key(root: Path):
    # `root` itself is part of the key: two engagement roots with matching
    # mtimes and no git history would otherwise collide on the same key and
    # the second root's dashboard would silently render the first's state.
    base = root / ENGAGEMENT_DIR
    return (
        root,
        history.head(root),
        _mtime(base / "engagement.md"),
        _mtime(base / "requirements.md"),
        _mtime(base / "tasks.md"),
        _mtime(base / "signoffs.md"),
        _mtime(base / "status.md"),
    )


def cached_state(root: Path) -> State:
    """`build_state` is expensive — one `git rev-parse`, plus per-sign-off and
    per-revision subprocess calls. The browser polls `/api/state` every two
    seconds, forever, per open tab, so the handler must never call
    `build_state` directly. This recomputes only when `HEAD` or one of the
    four engagement files' mtimes changes; otherwise it returns the same
    cached `State` object. `build_state` itself stays uncached so tests can
    call it deterministically.
    """
    key = _cache_key(root)
    with _CACHE_LOCK:
        entry = _cache.get(root)
        if entry is None or entry[0] != key:
            entry = (key, build_state(root))
            _cache[root] = entry
        return entry[1]


def _handler(entries):
    """`entries` is the ordered ((slug, root), ...) from `slugs`."""
    by_slug = {slug: root for slug, root in entries}
    single = entries[0][1] if len(entries) == 1 else None

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _root_for(self, query: str):
            """The engagement a request is about, or None if it names one we
            were not given. Never falls back to a different engagement — a
            dashboard silently showing the wrong client is the worst outcome
            this view can produce."""
            asked = (parse_qs(query).get("e") or [None])[0]
            if asked is not None:
                return by_slug.get(asked)
            return single

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            if path.startswith("/api/state"):
                root = self._root_for(parsed.query)
                if root is None:
                    self._send(404, b"unknown engagement", "text/plain; charset=utf-8")
                    return
                fragment = render.body(cached_state(root))
                digest = hashlib.sha256(fragment.encode()).hexdigest()[:16]
                payload = json.dumps(
                    {
                        "hash": digest,
                        "html": fragment,
                        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    }
                ).encode()
                self._send(200, payload, "application/json; charset=utf-8")
                return

            if path in ("/", "/index.html"):
                if single is not None:
                    body = render.page(cached_state(single))
                else:
                    rendered = tuple((slug, cached_state(r)) for slug, r in entries)
                    body = render.index_page(rendered)
                self._send(200, body.encode(), "text/html; charset=utf-8")
                return

            if path.startswith("/e/"):
                asked = path[len("/e/"):].strip("/")
                root = by_slug.get(asked)
                if root is None:
                    self._send(404, b"unknown engagement", "text/plain; charset=utf-8")
                    return
                state = cached_state(root)
                # The switcher needs every engagement's NAME, not just its
                # slug — a slug is a directory name and two clients can have
                # unhelpfully similar ones.
                siblings = tuple(
                    (s, cached_state(r).engagement.engagement.client
                     if cached_state(r).engagement.engagement else s)
                    for s, r in entries
                )
                self._send(
                    200,
                    render.page(state, siblings, asked).encode(),
                    "text/html; charset=utf-8",
                )
                return

            self._send(404, b"not found", "text/plain; charset=utf-8")

        def _reject(self):
            self._send(405, b"read-only: GET only", "text/plain; charset=utf-8")

        do_POST = do_PUT = do_DELETE = do_PATCH = _reject  # noqa: N815

        def log_message(self, *args):  # silence per-request stderr noise
            return

    return Handler


def serve(roots, port: int | None = None) -> None:
    """`roots` is one path or several. One renders the engagement at `/`,
    exactly as before; several render a portfolio index there, with each
    engagement at `/e/<slug>`."""
    if isinstance(roots, (str, Path)):
        roots = [roots]
    entries = slugs(roots)
    candidates = [port] if port else list(PORT_RANGE)
    for candidate in candidates:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), _handler(entries))
        except OSError:
            continue
        print(f"Engagement dashboard: http://127.0.0.1:{candidate}/", flush=True)
        if len(entries) > 1:
            for slug, root in entries:
                print(f"  /e/{slug}  {root}", flush=True)
        print("Read-only. Ctrl-C to stop.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return
    raise SystemExit(f"No free port in {PORT_RANGE.start}-{PORT_RANGE.stop - 1}.")
