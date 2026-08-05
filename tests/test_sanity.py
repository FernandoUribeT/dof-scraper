import pytest

from dof_scraper.parser import Note
from dof_scraper.sanity import SanityCheckFailed, check


def note(codigo="1", fecha="05/08/2026", titulo="Acuerdo por el que se algo"):
    return Note(codigo=codigo, fecha=fecha, titulo=titulo)


def many(n, **kw):
    return [note(codigo=str(i), **kw) for i in range(n)]


def test_a_healthy_scrape_passes():
    check(many(30))


def test_an_empty_scrape_is_a_failure_not_a_result():
    # The most dangerous outcome: the site changed, we parsed nothing, and the
    # pipeline records "0 documents today" as if that were the news.
    with pytest.raises(SanityCheckFailed, match="no documents"):
        check([])


def test_duplicate_codes_fail():
    with pytest.raises(SanityCheckFailed, match="duplicate"):
        check([note(codigo="7"), note(codigo="7")])


def test_implausible_year_fails():
    with pytest.raises(SanityCheckFailed, match="implausible"):
        check([note(fecha="05/08/1926")])


def test_empty_title_fails():
    with pytest.raises(SanityCheckFailed, match="title"):
        check([note(titulo="")])


def test_an_implausible_volume_fails():
    # The DOF does not publish two thousand notices in a day; a count like that
    # means the selector started matching navigation links.
    with pytest.raises(SanityCheckFailed, match="volume"):
        check(many(2000))


def test_every_problem_is_reported_not_just_the_first():
    with pytest.raises(SanityCheckFailed) as err:
        check([note(codigo="7", fecha="05/08/1926"), note(codigo="7", titulo="")])

    message = str(err.value)
    assert "duplicate" in message
    assert "implausible" in message
    assert "title" in message
