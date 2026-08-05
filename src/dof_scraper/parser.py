"""Parse the DOF front page into structured notes.

The front page has three defects this module compensates for. Each one is
handled explicitly rather than papered over, because a scraper that silently
returns wrong data is worse than one that returns nothing:

1. It declares ``charset=ISO-8859-1`` and ``charset=UTF-8`` in the same
   document while serving UTF-8 bytes. Trusting the declaration yields mojibake.
2. Links rendered by the ``enlaces_leido`` widget carry a year exactly 100 years
   in the past (``05/08/1926`` for a document published ``05/08/2026``). Those
   URLs 302 to an empty page, so following them silently loses documents.
3. The same document is often linked twice with contradictory dates — once from
   each widget. The ``enlaces`` variant carries the correct year, which makes the
   right date recoverable from the page itself instead of guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

NOTE_HREF = re.compile(r"codigo=(\d+)&fecha=(\d{2}/\d{2}/(\d{4}))")

#: The observed offset of the broken widget: it renders the year minus a century.
BROKEN_YEAR_OFFSET = 100

#: Years outside this window are not plausible DOF publication dates.
PLAUSIBLE_YEARS = range(2000, 2101)


@dataclass(frozen=True)
class Note:
    codigo: str
    fecha: str
    titulo: str


def repair_year(fecha: str, *, reference_year: int) -> str:
    """Undo the front page's hundred-year offset, and nothing else.

    Only a date that is *exactly* ``BROKEN_YEAR_OFFSET`` years before the
    reference is repaired. A genuinely historical date is left alone: the DOF
    publishes real notices from the last century, and rewriting those would
    corrupt data rather than fix it.
    """
    day, month, year = fecha.split("/")
    if int(year) == reference_year - BROKEN_YEAR_OFFSET:
        return f"{day}/{month}/{reference_year}"
    return fecha


def _reference_year(dates: list[str]) -> int:
    """The most recent plausible year the page states about itself.

    Derived from the page rather than from the clock, so parsing a saved page
    is deterministic and a test does not start failing on New Year's Day.
    """
    plausible = [int(d.split("/")[-1]) for d in dates if int(d.split("/")[-1]) in PLAUSIBLE_YEARS]
    return max(plausible) if plausible else 0


def parse_notes(html: bytes) -> list[Note]:
    """Return each distinct document linked from the front page.

    Documents linked twice with contradictory dates collapse to one entry
    carrying the date the page itself confirms.
    """
    soup = BeautifulSoup(html.decode("utf-8"), "html.parser")

    found: list[tuple[str, str, str]] = []
    for anchor in soup.find_all("a"):
        match = NOTE_HREF.search(anchor.get("href") or "")
        if not match:
            continue
        codigo, fecha, _ = match.groups()
        found.append((codigo, fecha, " ".join(anchor.get_text().split())))

    reference = _reference_year([fecha for _, fecha, _ in found])

    by_code: dict[str, Note] = {}
    for codigo, fecha, titulo in found:
        repaired = repair_year(fecha, reference_year=reference)
        existing = by_code.get(codigo)
        if existing is None:
            by_code[codigo] = Note(codigo=codigo, fecha=repaired, titulo=titulo)
        elif not existing.titulo and titulo:
            by_code[codigo] = Note(codigo=codigo, fecha=repaired, titulo=titulo)

    return list(by_code.values())
