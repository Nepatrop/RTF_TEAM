FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.4.9 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

COPY uv.lock pyproject.toml /app/
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen

COPY . /app

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "api_start.py"]
