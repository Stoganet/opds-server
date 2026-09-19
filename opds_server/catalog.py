"""Filesystem/epub inspection: walking the library, resolving ids, cover extraction."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote
from xml.etree import ElementTree as ET

OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}
CONTAINER_NS = {"cn": "urn:oasis:names:tc:opendocument:xmlns:container"}

EXT_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


@dataclass(frozen=True)
class Book:
    id: str
    title: str
    author: str
    path: Path


def iter_books(books_root: Path) -> list[Book]:
    """Walk books_root recursively, returning one Book per .epub found.

    Layout is Books/<Author>/<Title>/<file>.epub; title/author come from the
    two parent folder names so a corrupt or unopenable epub still lists.
    """
    if not books_root.is_dir():
        return []

    books = []
    for epub_path in sorted(books_root.rglob("*.epub")):
        if not epub_path.is_file():
            continue
        rel = epub_path.relative_to(books_root)
        author = rel.parts[-3] if len(rel.parts) >= 3 else ""
        title = rel.parts[-2] if len(rel.parts) >= 2 else rel.stem
        books.append(
            Book(
                id=quote(str(rel)),
                title=title,
                author=author,
                path=epub_path,
            )
        )
    return books


def resolve_id(books_root: Path, book_id: str) -> Path | None:
    """Resolve a URL-quoted id back to a real file under books_root.

    Returns None if the id doesn't decode to a file that actually exists
    inside books_root (missing, mistyped, or a path-traversal attempt).
    """
    try:
        rel = unquote(book_id)
    except (UnicodeDecodeError, ValueError):
        return None

    if not rel:
        return None

    candidate = (books_root / rel).resolve()
    root = books_root.resolve()

    if candidate != root and root not in candidate.parents:
        return None

    if not candidate.is_file():
        return None

    return candidate


def find_cover(epub_path: Path) -> tuple[bytes, str] | None:
    """Return (image_bytes, content_type) for the epub's declared cover, if any."""
    try:
        with zipfile.ZipFile(epub_path) as zf:
            opf_path, opf_root = _read_opf(zf)
            if opf_root is None:
                return None

            href = _find_cover_href(opf_root)
            if href is None:
                return None

            if opf_path.parent != Path("."):
                image_path = (opf_path.parent / href).as_posix()
            else:
                image_path = href
            image_bytes = zf.read(image_path)
    except (KeyError, zipfile.BadZipFile, ET.ParseError, OSError):
        return None

    ext = Path(href).suffix.lower()
    content_type = EXT_CONTENT_TYPES.get(ext)
    if content_type is None:
        return None

    return image_bytes, content_type


def _parse_xml(data: bytes) -> ET.Element:
    """Parse XML while rejecting any DOCTYPE, to block entity-expansion attacks.

    Neither container.xml nor an OPF manifest legitimately declares a
    DOCTYPE, so refusing one outright closes off billion-laughs-style
    payloads (their entity definitions live inside the DOCTYPE block)
    without needing a third-party XML-hardening library.
    """
    if b"<!DOCTYPE" in data:
        raise ET.ParseError("DOCTYPE declarations are not allowed")
    return ET.fromstring(data)


def _read_opf(zf: zipfile.ZipFile) -> tuple[Path, ET.Element | None]:
    container = _parse_xml(zf.read("META-INF/container.xml"))
    rootfile = container.find(".//cn:rootfile", CONTAINER_NS)
    if rootfile is None:
        return Path(""), None

    opf_full_path = rootfile.get("full-path")
    if not opf_full_path:
        return Path(""), None

    opf_root = _parse_xml(zf.read(opf_full_path))
    return Path(opf_full_path), opf_root


def _find_cover_href(opf_root: ET.Element) -> str | None:
    manifest = opf_root.find("opf:manifest", OPF_NS)
    if manifest is None:
        return None

    for item in manifest.findall("opf:item", OPF_NS):
        properties = item.get("properties", "")
        if "cover-image" in properties.split():
            return item.get("href")

    metadata = opf_root.find("opf:metadata", OPF_NS)
    cover_id = None
    if metadata is not None:
        for meta in metadata.findall("opf:meta", OPF_NS):
            if meta.get("name") == "cover":
                cover_id = meta.get("content")
                break

    if cover_id is None:
        return None

    for item in manifest.findall("opf:item", OPF_NS):
        if item.get("id") == cover_id:
            return item.get("href")

    return None
