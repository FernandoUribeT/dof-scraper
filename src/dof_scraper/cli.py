"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .fetcher import InsecureTransportRefused, fetch
from .parser import parse_notes
from .sanity import SanityCheckFailed, check

FRONT_PAGE = "https://www.dof.gob.mx/"

#: Stable, machine-readable failure marker written to stderr before exiting.
#: A caller — a cron job, a CI step, an n8n workflow — should never have to
#: pattern-match an English error sentence to know what went wrong. The prose
#: is for humans and may be reworded; this line is the contract.
FAILURE_MARKER = "dof-scraper: failure kind={kind}"


def _report_failure(kind: str, detail: str) -> None:
    print(FAILURE_MARKER.format(kind=kind), file=sys.stderr)
    print(f"error: {detail}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dof-scraper",
        description="Extract today's documents from the Diario Oficial de la Federación.",
        epilog=(
            "The DOF's TLS certificate is expired and its front page emits some links "
            "with a year 100 years in the past. Both are handled explicitly; see the README."
        ),
    )
    parser.add_argument("--url", default=FRONT_PAGE, help=f"page to scrape (default: {FRONT_PAGE})")
    parser.add_argument(
        "--insecure-tls",
        action="store_true",
        help="proceed when the certificate cannot be verified (prints a warning; off by default)",
    )
    parser.add_argument(
        "--skip-sanity-checks",
        action="store_true",
        help="emit results even if they look wrong (for debugging only)",
    )
    parser.add_argument("--file", help="parse a saved HTML file instead of fetching")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.file:
            html = open(args.file, "rb").read()
        else:
            html = fetch(args.url, allow_insecure_tls=args.insecure_tls)
    except InsecureTransportRefused as err:
        _report_failure("transport", str(err))
        return 2
    except OSError as err:
        _report_failure("transport", f"could not read input: {err}")
        return 2

    notes = parse_notes(html)

    if not args.skip_sanity_checks:
        try:
            check(notes)
        except SanityCheckFailed as err:
            _report_failure("data", f"sanity checks failed: {err}")
            print("refusing to emit results that should not be trusted.", file=sys.stderr)
            return 3

    json.dump([asdict(n) for n in notes], sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    print(f"{len(notes)} documents", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
