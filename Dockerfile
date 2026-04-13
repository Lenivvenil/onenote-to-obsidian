# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md LICENSE ./
COPY onenote_to_obsidian ./onenote_to_obsidian

RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Minimal runtime
FROM python:3.12-slim

COPY --from=builder /install /usr/local

COPY onenote_to_obsidian /app/onenote_to_obsidian

RUN useradd -m -u 1000 appuser && \
    mkdir -p /home/appuser/.onenote_exporter && \
    chown -R appuser:appuser /home/appuser

USER appuser
WORKDIR /home/appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["onenote-to-obsidian"]

LABEL org.opencontainers.image.title="OneNote to Obsidian Exporter" \
      org.opencontainers.image.description="Export OneNote notebooks to Obsidian Markdown" \
      org.opencontainers.image.url="https://github.com/Lenivvenil/onenote-to-obsidian" \
      org.opencontainers.image.source="https://github.com/Lenivvenil/onenote-to-obsidian" \
      org.opencontainers.image.licenses="MIT"
