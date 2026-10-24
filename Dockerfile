FROM python:3.15-slim@sha256:533b0b2f9b5d46fd097091cf826f27902f1d6c3bca714b6dc74551356aa97a51

WORKDIR /app

COPY pyproject.toml README.md ./
COPY opds_server ./opds_server

RUN pip install --no-cache-dir .

ENV BOOKS_ROOT=/books
EXPOSE 8082

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8082/opds')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8082", "opds_server.app:create_app()"]

