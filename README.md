# dof-scraper

Extracts the documents published each day by Mexico's **Diario Oficial de la Federación**
(dof.gob.mx) and emits them as JSON.

It is a small scraper with an opinion: **a scraper that returns wrong data silently is worse
than one that returns nothing loudly.** Every defect below is handled explicitly, and the
program refuses to emit results it cannot vouch for.

```bash
uv sync
uv run dof-scraper --insecure-tls        # see "Defect 1" for why the flag is needed today
uv run dof-scraper --file page.html      # parse a saved page, no network
```

```json
[
  {
    "codigo": "5795538",
    "fecha": "05/08/2026",
    "titulo": "Tipo de cambio para solventar obligaciones denominadas en moneda extranjera pagaderas en la República Mexicana."
  }
]
```

Exit codes: `0` success · `2` transport refused · `3` sanity checks failed.

---

## What is actually wrong with the source

All three were found by inspecting the live site on **2026-08-05**, and all three are
reproducible from the fixtures in `tests/fixtures/`.

### Defect 1 — the TLS certificate is expired, and the chain is broken

```
$ echo | openssl s_client -connect www.dof.gob.mx:443 -servername www.dof.gob.mx
 0 s:CN=dof.gob.mx
 1 s:CN=dof.gob.mx          <-- should be the GoDaddy intermediate, not the leaf again
Verify return code: 10 (certificate has expired)
```

The certificate expired at `Aug 5 20:48:45 2026 GMT`, and the server sends the leaf twice
instead of the intermediate, so the chain cannot be built either way.

**The easy fix is `verify=False`, and this project refuses to make it the default.** Disabling
verification means anyone on the network path can read and rewrite the response. For a tool
whose entire purpose is producing a trustworthy record of what a government gazette published,
that is not a minor trade-off. So:

- Without the flag, the run **fails closed** with an explanation and exit code `2`.
- `--insecure-tls` is an explicit, per-run decision that prints a warning to stderr every time.
- The warning is never suppressed, and insecure mode is never selected automatically.

When the DOF renews the certificate, the flag stops being necessary and nothing else changes.

### Defect 2 — the front page links to a year 100 years in the past

The `enlaces_leido` widget renders every link with the year minus a century:

```
/nota_detalle.php?codigo=5795536&fecha=05/08/1926   -> HTTP 302, empty page
/nota_detalle.php?codigo=5795536&fecha=05/08/2026   -> HTTP 200, the actual document
```

Same document, same code. A scraper that follows the front page links naively gets a redirect
to an empty page and records nothing — **without any error**, which is the failure mode that
matters.

### Defect 3 — the page contradicts itself, which is what makes it fixable

The same document is linked twice, once by each widget, with two different dates. Of 39 note
links on the front page, 23 carry the broken year and 16 carry the correct one, and five
documents appear in both groups:

```
5795536  enlaces        05/08/2026
5795536  enlaces_leido  05/08/1926
```

That contradiction is a gift: the correct year is recoverable **from the page itself** rather
than assumed. `repair_year` therefore only undoes a shift of exactly 100 years against a
reference the page states about itself, and leaves genuinely historical dates alone — the DOF
does publish real notices from the last century, and rewriting those would corrupt data while
appearing to fix it.

The reference year is derived from the page rather than the system clock, so parsing a saved
page is deterministic and the tests do not start failing on New Year's Day.

### Bonus — the declared encoding is wrong twice over

The page declares `charset=ISO-8859-1` **and** `charset=UTF-8` in the same document while
serving UTF-8 bytes. Trusting the first declaration turns *Federación* into *FederaciÃ³n*.
There is a test asserting that mojibake never reaches the output.

---

## Sanity checks

Results are validated before they count as results. The run fails with exit code `3` if any of
these hold, and reports **every** problem at once rather than the first:

| Check | Why |
|---|---|
| No documents extracted | The likeliest real failure: the markup changed and "0 today" gets recorded as news |
| Implausible volume (outside 1–500) | The selector started matching navigation links |
| Duplicate document codes | Deduplication broke |
| Implausible publication dates | The year repair failed or a new date defect appeared |
| Empty titles | The title is being read from the wrong node |

`--skip-sanity-checks` exists for debugging and is deliberately awkward to reach for.

---

## Design notes

- **Distinct documents, not links.** 39 anchors on the front page resolve to 34 distinct
  documents. The count that matters is documents.
- **Deterministic tests, no network.** Every test runs against saved fixtures. The HTTP layer
  is tested through an injected session, so TLS policy is verified without a live certificate.
- **Fail closed everywhere.** Bad transport, bad data and unverifiable results all stop the run
  instead of degrading it.

## Development

```bash
uv sync
uv run pytest
```

21 tests, all offline.

## Scope and etiquette

Reads only public pages of a government gazette — the documents are published for public
consumption. It identifies itself in the `User-Agent`, makes one request per run, does not
attempt to authenticate, and does not try to defeat any access control. It is not affiliated
with the Diario Oficial de la Federación.

MIT.
