from urllib.parse import quote
from xml.etree import ElementTree as ET

ATOM_NS = "{http://www.w3.org/2005/Atom}"

HAS_COVER_REL = "Jane Author/Has Cover Book/Has Cover Book - Jane Author.epub"
NO_COVER_REL = "John Writer/No Cover Book/No Cover Book - John Writer.epub"


def test_lists_exactly_the_epub_fixtures(client):
    resp = client.get("/opds")
    root = ET.fromstring(resp.data)
    entries = root.findall(f"{ATOM_NS}entry")
    titles = {e.find(f"{ATOM_NS}title").text for e in entries}
    assert titles == {"Has Cover Book", "No Cover Book", "Corrupt Book"}


def test_title_and_author_from_folder_names(client):
    resp = client.get("/opds")
    root = ET.fromstring(resp.data)
    entries = root.findall(f"{ATOM_NS}entry")
    by_title = {e.find(f"{ATOM_NS}title").text: e for e in entries}

    entry = by_title["Has Cover Book"]
    author = entry.find(f"{ATOM_NS}author/{ATOM_NS}name").text
    assert author == "Jane Author"


def test_thumbnail_link_only_for_book_with_cover(client):
    resp = client.get("/opds")
    root = ET.fromstring(resp.data)
    entries = root.findall(f"{ATOM_NS}entry")
    by_title = {e.find(f"{ATOM_NS}title").text: e for e in entries}

    def thumb_links(entry):
        return [
            link
            for link in entry.findall(f"{ATOM_NS}link")
            if link.get("rel") == "http://opds-spec.org/image/thumbnail"
        ]

    assert len(thumb_links(by_title["Has Cover Book"])) == 1
    assert len(thumb_links(by_title["No Cover Book"])) == 0
    assert len(thumb_links(by_title["Corrupt Book"])) == 0


def test_feed_is_well_formed_with_opds_namespace(client):
    resp = client.get("/opds")
    assert resp.status_code == 200
    assert resp.mimetype == "application/atom+xml"
    root = ET.fromstring(resp.data)
    assert root.tag == f"{ATOM_NS}feed"

    acquisition_links = root.findall(
        f".//{ATOM_NS}entry/{ATOM_NS}link[@rel='http://opds-spec.org/acquisition']"
    )
    assert len(acquisition_links) == 3
    for link in acquisition_links:
        assert link.get("type") == "application/epub+zip"


def test_cover_returns_exact_embedded_bytes(client, books_root):
    epub_id = quote(HAS_COVER_REL)
    resp = client.get(f"/covers/{epub_id}.jpg")
    assert resp.status_code == 200
    assert resp.mimetype == "image/jpeg"

    import zipfile

    with zipfile.ZipFile(books_root / HAS_COVER_REL) as zf:
        expected = zf.read("OEBPS/cover.jpg")
    assert resp.data == expected


def test_cover_404_for_no_cover_fixture(client):
    epub_id = quote(NO_COVER_REL)
    resp = client.get(f"/covers/{epub_id}.jpg")
    assert resp.status_code == 404


def test_cover_404_for_corrupt_fixture(client):
    corrupt_rel = "Corrupt Author/Corrupt Book/Corrupt Book - Corrupt Author.epub"
    epub_id = quote(corrupt_rel)
    resp = client.get(f"/covers/{epub_id}.jpg")
    assert resp.status_code == 404


def test_download_streams_correct_bytes_and_headers(client, books_root):
    epub_id = quote(HAS_COVER_REL)
    resp = client.get(f"/books/{epub_id}")
    assert resp.status_code == 200
    assert resp.mimetype == "application/epub+zip"
    assert "Has Cover Book - Jane Author.epub" in resp.headers["Content-Disposition"]
    assert resp.data == (books_root / HAS_COVER_REL).read_bytes()


def test_path_traversal_id_rejected(client):
    resp = client.get("/books/..%2F..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code == 404

    resp = client.get("/covers/..%2F..%2Fetc%2Fpasswd.jpg")
    assert resp.status_code == 404


def test_nonexistent_id_returns_404(client):
    resp = client.get("/books/does%2Fnot%2Fexist.epub")
    assert resp.status_code == 404


def test_empty_books_root_returns_valid_empty_feed(tmp_path):
    from opds_server.app import create_app

    app = create_app(tmp_path / "does-not-exist")
    client = app.test_client()

    resp = client.get("/opds")
    assert resp.status_code == 200
    root = ET.fromstring(resp.data)
    assert root.findall(f"{ATOM_NS}entry") == []
