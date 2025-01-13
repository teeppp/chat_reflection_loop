FROM python:3.12-slim AS base

RUN apt-get update -y && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    graphviz graphviz-dev

FROM base AS base_uv
# install UV
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

FROM base_uv AS base_backend
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./uv.lock,target=uv.lock \
    --mount=type=bind,source=./pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

FROM base AS backend
COPY --from=base_backend --chown=app:app /app/.venv /app/.venv
COPY . /app
WORKDIR /app
EXPOSE 8080
CMD ["/app/.venv/bin/fastapi","run", "api.py", "--host", "0.0.0.0", "--port", "8080"]