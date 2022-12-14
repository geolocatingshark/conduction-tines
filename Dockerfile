FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y gcc libffi-dev g++ git
WORKDIR /app

FROM base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.2.2

RUN pip install "poetry==$POETRY_VERSION"
RUN python -m venv /venv

COPY pyproject.toml poetry.lock ./
RUN . /venv/bin/activate && poetry install --no-dev --no-root

COPY . .
RUN . /venv/bin/activate && poetry build

FROM base as final

COPY --from=builder /venv /venv
COPY --from=builder /app/dist .
COPY docker-entrypoint.sh ./
COPY Procfile ./

RUN . /venv/bin/activate && pip install *.whl
CMD ["./docker-entrypoint.sh"]