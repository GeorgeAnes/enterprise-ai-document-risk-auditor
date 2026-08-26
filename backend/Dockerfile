# Build context is the repo root: docker build -f backend/Dockerfile .
# (needed so data/samples/ is reachable -- it lives outside backend/)

# ---- builder: install deps into an isolated venv ----
FROM python:3.12-slim AS builder

WORKDIR /build

COPY backend/requirements.txt ./requirements.txt
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir -r requirements.txt

# ---- runtime: app + venv only, no build tooling ----
FROM python:3.12-slim AS runtime

RUN useradd --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY backend/app/ ./backend/app/
COPY backend/__init__.py ./backend/__init__.py
COPY data/samples/ ./data/samples/

# Scoped copies above intentionally exclude backend/tests/, data/raw/,
# data/private/, data/external/, data/eval/ -- none of it belongs in a
# public image, and data/samples/ is the only data the app reads at
# runtime (REPO_ROOT/data/samples in backend/app/main.py).

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
