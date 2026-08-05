import pytest
import requests

from dof_scraper.fetcher import InsecureTransportRefused, fetch


class FakeSession:
    """Stands in for requests.Session, recording how it was called."""

    def __init__(self, *, raises=None, body=b"<html></html>"):
        self.raises = raises
        self.body = body
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.raises:
            raise self.raises
        response = requests.Response()
        response.status_code = 200
        response._content = self.body
        response.url = url
        return response


def test_verifies_tls_by_default():
    session = FakeSession()

    fetch("https://www.dof.gob.mx/", session=session)

    _, kwargs = session.calls[0]
    assert kwargs["verify"] is True


def test_expired_certificate_fails_closed():
    session = FakeSession(raises=requests.exceptions.SSLError("certificate has expired"))

    with pytest.raises(InsecureTransportRefused) as err:
        fetch("https://www.dof.gob.mx/", session=session)

    assert "--insecure-tls" in str(err.value)


def test_insecure_mode_is_opt_in_and_never_silent(capsys):
    session = FakeSession(raises=requests.exceptions.SSLError("certificate has expired"))

    with pytest.raises(InsecureTransportRefused):
        fetch("https://www.dof.gob.mx/", session=session)
    assert capsys.readouterr().err == ""

    session = FakeSession()
    fetch("https://www.dof.gob.mx/", session=session, allow_insecure_tls=True)

    warning = capsys.readouterr().err
    assert "WARNING" in warning
    assert "not verified" in warning


def test_insecure_mode_disables_verification_only_when_asked():
    session = FakeSession()

    fetch("https://www.dof.gob.mx/", session=session, allow_insecure_tls=True)

    _, kwargs = session.calls[0]
    assert kwargs["verify"] is False


def test_identifies_itself_in_the_user_agent():
    session = FakeSession()

    fetch("https://www.dof.gob.mx/", session=session)

    _, kwargs = session.calls[0]
    assert "dof-scraper" in kwargs["headers"]["User-Agent"]
