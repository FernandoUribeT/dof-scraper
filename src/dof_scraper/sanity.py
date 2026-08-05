"""Sanity checks run before a scrape is allowed to count as a result.

A scraper's worst failure is not crashing — it is returning a clean, plausible,
empty answer after the site changed underneath it. These checks turn that
silence into an error, and report every problem at once so one run tells you
everything that is wrong instead of one thing per fix.
"""

from __future__ import annotations

from collections import Counter

from .parser import Note

#: The DOF publishes tens of notices on a normal day, never thousands. A count
#: outside this band means the selector is matching the wrong thing.
EXPECTED_VOLUME = range(1, 501)

PLAUSIBLE_YEARS = range(2000, 2101)


class SanityCheckFailed(AssertionError):
    """The scrape produced data that should not be trusted downstream."""


def problems(notes: list[Note]) -> list[str]:
    """Every reason this scrape should not be trusted, in report order."""
    found = []

    if not notes:
        return ["no documents were extracted — the page structure probably changed"]

    if len(notes) not in EXPECTED_VOLUME:
        found.append(
            f"implausible volume: {len(notes)} documents, expected "
            f"{EXPECTED_VOLUME.start}-{EXPECTED_VOLUME.stop - 1}"
        )

    duplicated = [code for code, n in Counter(n.codigo for n in notes).items() if n > 1]
    if duplicated:
        found.append(f"duplicate document codes: {', '.join(sorted(duplicated))}")

    bad_years = sorted(
        {n.fecha for n in notes if int(n.fecha.split("/")[-1]) not in PLAUSIBLE_YEARS}
    )
    if bad_years:
        found.append(f"implausible publication dates: {', '.join(bad_years)}")

    untitled = sorted(n.codigo for n in notes if not n.titulo.strip())
    if untitled:
        found.append(f"documents with an empty title: {', '.join(untitled)}")

    return found


def check(notes: list[Note]) -> list[Note]:
    """Return ``notes`` unchanged, or raise with every problem found."""
    found = problems(notes)
    if found:
        raise SanityCheckFailed("; ".join(found))
    return notes
