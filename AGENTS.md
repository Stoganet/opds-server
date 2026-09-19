# AGENTS.md

Guidance for coding agents working in this repo.

See README.md for what this project is and does.

## Layout

Stdlib-only for filesystem/epub handling — no third-party epub library, on purpose.

- `opds_server/catalog.py` — filesystem/epub inspection: walking the library, id
  resolution, cover extraction. No Flask imports here.
- `opds_server/feed.py` — pure XML feed builder (ElementTree), no filesystem access beyond
  what `catalog.py` hands it.
- `opds_server/app.py` — Flask routes, thin glue over the above two.

## Architecture invariants

- **Book ids are URL-quoted paths relative to `BOOKS_ROOT`**, not database rows or UUIDs.
  `resolve_id()` in `catalog.py` is the only place that turns an id back into a filesystem
  path, and it must keep the `root not in candidate.parents` traversal guard — that's the
  entire defense against `../../etc/passwd`-style ids. Don't add a second path-resolution
  code path that skips it.
- **XML parsing always goes through `_parse_xml()`** in `catalog.py`, never
  `ET.fromstring()` directly. It rejects any `<!DOCTYPE` before parsing, which is what
  blocks billion-laughs-style entity-expansion payloads embedded in a malicious EPUB's
  `container.xml` or OPF. Untrusted epub files are the attack surface here — a user's
  Chaptarr library is not curated for safety.
- **Cover content-type is derived from the actual image bytes' extension inside the epub**
  (`EXT_CONTENT_TYPES` in `catalog.py`), not assumed. The reverse map
  (`CONTENT_TYPE_EXTENSIONS` in `catalog.py`) drives the thumbnail URL extension in
  `feed.py` — keep both maps in sync if a new image format is ever added.
- **Downloads use `send_file(..., conditional=True)`**, not `read_bytes()` into a
  `Response`. This is what makes Range requests (resumable downloads, e-reader clients)
  work and avoids loading a whole epub into memory.
- **No caching layer.** Feed and cover generation re-read the filesystem/zip on every
  request. This is intentional for a personal-scale library; don't add a cache uninvited.

## Common operations

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/ruff check .
```

## Never

- Never write a commit message that isn't Conventional Commits (`fix:`, `feat:`, ...).
  Keep the body to one or two short paragraphs explaining what and why, not a bullet list.

## Deploy

Built and pushed to `ghcr.io/stoganet/opds-server` by `.github/workflows/deploy.yml` on
push to main. `Stoganet/infra` runs the actual container, mesh-only via NetBird — see that
repo's `AGENTS.md` for the invariants around port binding and no WAN exposure.

## Code review

`claude-code-review.yml` reads this file before reviewing a PR. Any violation of an
Architecture invariant above is Important. Everything else — style, naming, refactoring —
is Nit at most; cap at five per review, say "plus N similar items" if there are more.

Don't flag: formatting/import-order (ruff already enforces it in CI), missing caching
(a deliberate invariant, not an omission), or anything in `tests/fixtures/` (generated
binary content).

If all findings are nits, lead the summary with "No blocking issues."
