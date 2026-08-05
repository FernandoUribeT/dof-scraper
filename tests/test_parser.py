from pathlib import Path

import pytest

from dof_scraper.parser import parse_notes, repair_year

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def portada() -> bytes:
    return (FIXTURES / "dof-portada.html").read_bytes()


@pytest.fixture(scope="module")
def notes(portada):
    return parse_notes(portada)


def test_extracts_every_distinct_note(notes):
    # 39 anchors on the page, but 5 documents are linked twice (once from each
    # widget), so 34 distinct documents is the real answer.
    assert len(notes) == 34


def test_returns_each_document_once(notes):
    codes = [n.codigo for n in notes]

    assert len(codes) == len(set(codes))


def test_note_carries_code_date_and_title(notes):
    first = next(n for n in notes if n.codigo == "5795536")

    assert first.fecha == "05/08/2026"
    assert first.titulo.startswith("Modificación a los Anexos 1 y 2")


def test_accented_titles_survive_the_declared_encoding(notes):
    # The page declares ISO-8859-1 *and* UTF-8 while serving UTF-8 bytes.
    # Trusting the first declaration yields "Federación"-style mojibake.
    titles = " ".join(n.titulo for n in notes)

    assert "Ã³" not in titles
    assert "ó" in titles


def test_contradictory_dates_resolve_to_the_year_the_page_itself_confirms(notes):
    # Five documents are linked with two different years on the same page.
    # The `enlaces` variant carries the correct one; `enlaces_leido` is 100 years off.
    for codigo in ("5795536", "5795538", "5795519", "5795543"):
        note = next(n for n in notes if n.codigo == codigo)
        assert note.fecha.endswith("/2026"), f"{codigo} kept the broken year"


def test_no_note_keeps_an_implausible_year(notes):
    for note in notes:
        year = int(note.fecha.split("/")[-1])
        assert 2000 <= year <= 2100, f"{note.codigo} has year {year}"


# --- repair_year: the offset rule, isolated from parsing --------------------


def test_repair_year_shifts_the_hundred_year_offset():
    assert repair_year("05/08/1926", reference_year=2026) == "05/08/2026"


def test_repair_year_leaves_a_plausible_date_untouched():
    assert repair_year("05/08/2026", reference_year=2026) == "05/08/2026"


def test_repair_year_does_not_invent_a_shift_it_cannot_justify():
    # 1998 is a real DOF year, not an off-by-a-century artefact. Repairing it
    # would silently rewrite genuine historical data.
    assert repair_year("05/08/1998", reference_year=2026) == "05/08/1998"
