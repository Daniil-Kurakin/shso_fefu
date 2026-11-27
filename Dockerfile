FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY tsconfig.json vite.config.mjs ./
COPY frontend/ ./frontend/
COPY apps/ ./apps/
COPY templates/ ./templates/
COPY static/js/ ./static/js/
RUN npm run build

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv

WORKDIR /app

# Зависимости ставим отдельным слоем: кэш не сбрасывается при правке кода.
# Виртуальное окружение лежит вне /app, поэтому bind-mount исходников его не перекрывает.
ARG INSTALL_DEV=false
COPY pyproject.toml uv.lock* ./
RUN if [ "$INSTALL_DEV" = "true" ]; then uv sync; else uv sync --no-dev; fi

COPY . .
COPY --from=frontend /build/frontend/dist /opt/shso-static

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R app:app /app/media /app/staticfiles
USER app

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
