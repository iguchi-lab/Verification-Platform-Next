FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=8080 \
    VERIFICATION_OUTPUT_DIR=/tmp/verification-platform

WORKDIR /app

RUN python -m pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml ./
COPY apps/gradio/pyproject.toml apps/gradio/pyproject.toml
COPY packages/verification-core/pyproject.toml packages/verification-core/pyproject.toml
COPY packages/pyhees-jjj/pyproject.toml packages/pyhees-jjj/pyproject.toml
COPY apps/gradio/src apps/gradio/src
COPY packages/verification-core/src packages/verification-core/src
COPY packages/pyhees-jjj/src packages/pyhees-jjj/src
COPY packages/pyhees-jjj/LICENSE packages/pyhees-jjj/LICENSE

RUN poetry install --only main --no-interaction --no-ansi

EXPOSE 8080

CMD ["verification-platform"]
