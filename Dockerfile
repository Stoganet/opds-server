FROM python:3.15-slim@sha256:d802f03223b9e00604cd54574bcac1a4638914c43683d3f0afd6ebee35f25313

WORKDIR /app

COPY pyproject.toml README.md ./
COPY opds_server ./opds_server

RUN pip install --no-cache-dir .

ENV BOOKS_ROOT=/books
EXPOSE 8082

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8082/opds')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8082", "opds_server.app:create_app()"]

