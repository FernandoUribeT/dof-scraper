"""HTTP transport for dof.gob.mx.

The DOF's TLS certificate is, as of 2026-08-05, expired and served with a broken
chain (the leaf is sent twice instead of the intermediate). The tempting fix is
``verify=False``. This module refuses to do that by default.

Disabling certificate verification means any party on the path can read and
rewrite the responses — on a scraper whose whole purpose is producing a trusted
record of what a government gazette published, that is not a small compromise.
So the failure is loud, the workaround is explicit, and choosing it prints a
warning every time.
"""

from __future__ import annotations

import sys

import requests

USER_AGENT = "dof-scraper/0.1 (+https://github.com/FernandoUribeT)"
TIMEOUT_SECONDS = 30


class InsecureTransportRefused(RuntimeError):
    """TLS verification failed and insecure transport was not authorised."""


def fetch(
    url: str,
    *,
    session=None,
    allow_insecure_tls: bool = False,
    timeout: int = TIMEOUT_SECONDS,
) -> bytes:
    """Fetch ``url``, failing closed when the certificate cannot be verified.

    Pass ``allow_insecure_tls=True`` only when you have independently confirmed
    why verification fails and accept that the response is unauthenticated.
    """
    session = session or requests.Session()

    if allow_insecure_tls:
        print(
            f"WARNING: TLS certificate for {url} is not verified. "
            "The response is unauthenticated and may have been modified in transit.",
            file=sys.stderr,
        )

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            verify=not allow_insecure_tls,
            timeout=timeout,
        )
    except requests.exceptions.SSLError as err:
        raise InsecureTransportRefused(
            f"TLS verification failed for {url}: {err}. "
            "Refusing to continue over an unauthenticated connection. "
            "Re-run with --insecure-tls if you have confirmed the cause and accept the risk."
        ) from err

    response.raise_for_status()
    return response.content
