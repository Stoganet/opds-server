"""OPDS Atom feed generation."""

from __future__ import annotations

from datetime import UTC, datetime
from xml.etree import ElementTree as ET

from .catalog import Book, CONTENT_TYPE_EXTENSIONS, find_cover

ATOM_NS = "http://www.w3.org/2005/Atom"
OPDS_NS = "http://opds-spec.org/2010/catalog"
ACQUISITION_TYPE = "application/epub+zip"
FEED_TYPE = "application/atom+xml;profile=opds-catalog;kind=acquisition"

ET.register_namespace("", ATOM_NS)


def build_feed(books: list[Book], base_url: str) -> str:
    base_url = base_url.rstrip("/")

    root = ET.Element(f"{{{ATOM_NS}}}feed")
    root.set("xmlns:opds", OPDS_NS)

    ET.SubElement(root, f"{{{ATOM_NS}}}id").text = f"{base_url}/opds"
    ET.SubElement(root, f"{{{ATOM_NS}}}title").text = "Library"
    ET.SubElement(root, f"{{{ATOM_NS}}}updated").text = datetime.now(UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    self_link = ET.SubElement(root, f"{{{ATOM_NS}}}link")
    self_link.set("rel", "self")
    self_link.set("href", f"{base_url}/opds")
    self_link.set("type", FEED_TYPE)

    for book in books:
        _add_entry(root, book, base_url)

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _add_entry(feed: ET.Element, book: Book, base_url: str) -> None:
    entry = ET.SubElement(feed, f"{{{ATOM_NS}}}entry")
    ET.SubElement(entry, f"{{{ATOM_NS}}}id").text = f"{base_url}/books/{book.id}"
    ET.SubElement(entry, f"{{{ATOM_NS}}}title").text = book.title
    author = ET.SubElement(entry, f"{{{ATOM_NS}}}author")
    ET.SubElement(author, f"{{{ATOM_NS}}}name").text = book.author

    acquisition = ET.SubElement(entry, f"{{{ATOM_NS}}}link")
    acquisition.set("rel", "http://opds-spec.org/acquisition")
    acquisition.set("href", f"{base_url}/books/{book.id}")
    acquisition.set("type", ACQUISITION_TYPE)

    cover = find_cover(book.path)
    if cover is not None:
        _, content_type = cover
        ext = CONTENT_TYPE_EXTENSIONS[content_type]
        thumbnail = ET.SubElement(entry, f"{{{ATOM_NS}}}link")
        thumbnail.set("rel", "http://opds-spec.org/image/thumbnail")
        thumbnail.set("href", f"{base_url}/covers/{book.id}{ext}")
        thumbnail.set("type", content_type)
