"""Entry point: python3 scripts/dashboard --root <path>"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    # `python3 scripts/dashboard` runs this file directly rather than via
    # `python3 -m`, so it has no parent package and the relative import
    # below would raise ImportError. Put `scripts/` on sys.path so
    # `dashboard` resolves as a top-level package instead — its own
    # internal relative imports (serve.py's `from . import analyse, ...`)
    # then work normally because `dashboard` is a real package.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dashboard.serve import ENGAGEMENT_DIR, serve
else:
    from .serve import ENGAGEMENT_DIR, serve


def main() -> int:
    parser = argparse.ArgumentParser(prog="dashboard", description="Engagement dashboard")
    parser.add_argument(
        "--root",
        nargs="+",
        default=["."],
        help="client repository root; give several for a portfolio view",
    )
    parser.add_argument("--port", type=int, default=None, help="override the default port")
    args = parser.parse_args()

    roots = [Path(r).resolve() for r in args.root]
    missing = [r for r in roots if not (r / ENGAGEMENT_DIR / "engagement.md").exists()]

    if len(missing) == len(roots):
        # Nothing to serve. Name every path and why, rather than reporting only
        # the first — someone who mistyped one of five wants to see which.
        print(
            f"No {ENGAGEMENT_DIR / 'engagement.md'} under any of:",
            file=sys.stderr,
        )
        for root in missing:
            print(f"  {root}", file=sys.stderr)
        print(
            "None of these is an engagement — run /new-engagement first.",
            file=sys.stderr,
        )
        return 1

    if missing:
        # Some are real. Serve them, but say plainly which are not, because the
        # index lists them too and a silent omission would misrepresent the
        # portfolio.
        for root in missing:
            print(f"Not an engagement, listed but empty: {root}", file=sys.stderr)

    serve(roots, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
