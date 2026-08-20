"""All git access. Every function is total: git failures become a documented
return value, never an exception and never a favourable default."""

from __future__ import annotations

import subprocess
from pathlib import Path

_TIMEOUT = 10


def _run(root: Path, *args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["git", "--no-pager", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def is_repo(root: Path) -> bool:
    result = _run(root, "rev-parse", "--git-dir")
    return result is not None and result.returncode == 0


def head(root: Path) -> str:
    result = _run(root, "rev-parse", "HEAD")
    if result is None or result.returncode != 0:
        return ""
    return result.stdout.strip()


def artifact_status(root: Path, commit: str, relpath: str) -> str:
    """Has `relpath` changed since `commit`?

    Returns "unchanged", "changed", or "unverifiable". A commit that is not in
    this repository must never read as "unchanged" — an approval that cannot be
    checked is not an approval that holds. Likewise, a path that did not exist
    in the tree at `commit` is "unverifiable", never "unchanged": `git diff
    --quiet` exits 0 for a path with no history at all (an empty path set has
    no differences), and reading that as "unchanged" would render a green tick
    for an approval that was never actually checked against anything.
    """
    if not commit or commit.startswith("-"):
        return "unverifiable"

    exists = _run(root, "cat-file", "-e", f"{commit}^{{commit}}")
    if exists is None or exists.returncode != 0:
        return "unverifiable"

    present_then = _run(root, "cat-file", "-e", f"{commit}:{relpath}")
    if present_then is None or present_then.returncode != 0:
        return "unverifiable"

    result = _run(root, "diff", "--quiet", commit, "HEAD", "--", relpath)
    if result is None:
        return "unverifiable"
    if result.returncode == 0:
        return "unchanged"
    if result.returncode == 1:
        return "changed"
    return "unverifiable"


def commit_exists(root: Path, sha: str) -> bool | None:
    """Is `sha` a commit in this repository?

    `artifact_status` deliberately answers a different question and returns
    "unverifiable" for BOTH a missing commit and a path that was not in the
    tree at that commit — for its purpose the two are the same, because
    neither can be diffed. A conformance report must tell them apart: one says
    the recorded approval points at nothing, the other says the artifact was
    not there yet. Returns None when git could not be RUN at all (missing
    binary, timeout) — "cannot tell", which must never be rendered as False.
    Outside a repository git runs and answers no, so this returns False there;
    callers that care about the difference check `is_repo` first, as
    `conform.py` does.
    """
    if not sha or sha.startswith("-"):
        return False
    result = _run(root, "cat-file", "-e", f"{sha}^{{commit}}")
    if result is None:
        return None
    return result.returncode == 0


def revisions(root: Path, relpath: str) -> tuple[bool, tuple[tuple[str, str], ...]]:
    """Every committed version of `relpath`, oldest first, as (iso_date, content).

    Returns `(ok, revisions)`. `ok` is False when `git log` itself could not
    be read (corrupt object store, permissions, timeout) — a fact distinct
    from "git ran fine and this path has no history", which is `ok=True`
    with an empty tuple. Conflating the two lets the renderer assert a false
    positive ("no committed history yet") when it actually could not check.

    A revision whose blob cannot be read is still returned, with empty string
    content, rather than dropped. The empty content fails to parse downstream,
    which is what renders it as a gap in the trend — never interpolated over,
    and never silently missing from the commit count either.
    """
    log = _run(root, "log", "--format=%H %cI", "--reverse", "--", relpath)
    if log is None or log.returncode != 0:
        return False, ()

    out: list[tuple[str, str]] = []
    for line in log.stdout.splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        sha, when = parts
        blob = _run(root, "show", f"{sha}:{relpath}")
        if blob is None or blob.returncode != 0:
            out.append((when.strip(), ""))
            continue
        out.append((when.strip(), blob.stdout))
    return True, tuple(out)


ENGAGEMENT_PREFIX = "docs/engagement/"


def file_at(root: Path, sha: str, relpath: str) -> tuple[bool, str | None]:
    """(ok, content) for `relpath` at `sha`.

    ok=False  — git could not be read (bad commit, corrupt repo, timeout).
                The caller must treat this as "cannot tell", never as an
                absent file.
    ok=True, content=None — the path genuinely was not in the tree at that
                commit. That is a real answer, distinct from a failed read.

    Existence is checked with `git cat-file -e` before the content is read,
    so a `git show` that fails after that check has already passed is a
    genuine failure rather than an absence.
    """
    commit_ok = _run(root, "cat-file", "-e", f"{sha}^{{commit}}")
    if commit_ok is None or commit_ok.returncode != 0:
        return False, None

    exists = _run(root, "cat-file", "-e", f"{sha}:{relpath}")
    if exists is None:
        return False, None
    if exists.returncode != 0:
        return True, None

    result = _run(root, "show", f"{sha}:{relpath}")
    if result is None or result.returncode != 0:
        return False, None
    return True, result.stdout


def engagement_commits(root: Path) -> tuple[bool, tuple[tuple[str, str, tuple[str, ...]], ...]]:
    """Every commit touching docs/engagement/, oldest first, as
    (sha, iso_date, changed_paths).

    Returns (ok, commits). `ok` is False when git itself could not be read, so
    the caller can distinguish "no history" from "cannot read history" — the
    same distinction `revisions` makes.
    """
    result = _run(
        root,
        "log",
        "--reverse",
        "--diff-merges=first-parent",
        "--format=%x00%H %cI",
        "--name-only",
        "--",
        ENGAGEMENT_PREFIX,
    )
    if result is None or result.returncode != 0:
        return False, ()

    commits = []
    for block in result.stdout.split("\x00"):
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        header = lines[0].split(None, 1)
        if len(header) != 2:
            continue
        sha, when = header[0], header[1].strip()
        paths = tuple(p for p in lines[1:] if p.startswith(ENGAGEMENT_PREFIX))
        commits.append((sha, when, paths))
    return True, tuple(commits)
