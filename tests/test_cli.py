import json
from pathlib import Path

import pytest

from dof_scraper import cli

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_a_local_file_and_emits_json(capsys):
    code = cli.main(["--file", str(FIXTURES / "dof-portada.html")])

    assert code == 0
    documents = json.loads(capsys.readouterr().out)
    assert len(documents) == 34


def test_sanity_failure_exits_three_with_a_machine_readable_marker(capsys):
    # The note page has no document links at all.
    code = cli.main(["--file", str(FIXTURES / "dof-nota.html")])

    assert code == 3
    err = capsys.readouterr().err
    assert "dof-scraper: failure kind=data" in err


def test_transport_failure_exits_two_with_a_machine_readable_marker(capsys, monkeypatch):
    def refuse(*args, **kwargs):
        raise cli.InsecureTransportRefused("certificate has expired")

    monkeypatch.setattr(cli, "fetch", refuse)

    code = cli.main([])

    assert code == 2
    err = capsys.readouterr().err
    assert "dof-scraper: failure kind=transport" in err


def test_the_marker_is_stable_regardless_of_the_prose(capsys, monkeypatch):
    # The marker exists so a caller never has to pattern-match an error
    # sentence. Rewording the message must not break the contract.
    def refuse(*args, **kwargs):
        raise cli.InsecureTransportRefused("completely different wording here")

    monkeypatch.setattr(cli, "fetch", refuse)
    cli.main([])

    assert "dof-scraper: failure kind=transport" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ["transport", "data"])
def test_marker_uses_one_stable_prefix(kind):
    assert cli.FAILURE_MARKER.format(kind=kind) == f"dof-scraper: failure kind={kind}"
