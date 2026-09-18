"""Flask application: OPDS feed, cover extraction, book download."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, Response, abort, request, send_file

from .catalog import find_cover, iter_books, resolve_id
from .feed import FEED_TYPE, build_feed


def create_app(books_root: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["BOOKS_ROOT"] = Path(
        books_root or os.environ.get("BOOKS_ROOT", "/books")
    )

    @app.get("/opds")
    def opds_feed() -> Response:
        root = app.config["BOOKS_ROOT"]
        books = iter_books(root)
        base_url = request.url_root
        xml = build_feed(books, base_url)
        return Response(xml, mimetype=FEED_TYPE)

    @app.get("/covers/<path:book_id>.jpg")
    def cover(book_id: str) -> Response:
        root = app.config["BOOKS_ROOT"]
        epub_path = resolve_id(root, book_id)
        if epub_path is None:
            abort(404)

        cover_data = find_cover(epub_path)
        if cover_data is None:
            abort(404)

        image_bytes, content_type = cover_data
        return Response(image_bytes, mimetype=content_type)

    @app.get("/books/<path:book_id>")
    def download(book_id: str):
        root = app.config["BOOKS_ROOT"]
        epub_path = resolve_id(root, book_id)
        if epub_path is None:
            abort(404)

        return send_file(
            epub_path,
            mimetype="application/epub+zip",
            as_attachment=True,
            download_name=epub_path.name,
            conditional=True,
        )

    return app
