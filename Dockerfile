FROM python:3.12.8-slim AS python-base
ENV PYTHONUNBUFFERED=1 \
    # prevents python creating .pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    \
    # pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    \
    # poetry
    # https://python-poetry.org/docs/configuration/#using-environment-variables
    POETRY_VERSION=1.8.5 \
    # make poetry create the virtual environment in the project's root
    # it gets named `.venv`
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    # do not ask any interactive question
    POETRY_NO_INTERACTION=1

FROM python-base AS builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        # deps for installing poetry
        curl \
        # deps for building python deps
        build-essential

# install poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python
# RUN export PATH="/opt/poetry/bin:$PATH"

# copy project requirement files here to ensure they will be cached.
COPY poetry.lock pyproject.toml ./

# install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
# RUN /opt/poetry/bin/poetry install
RUN /root/.local/bin/poetry export --without-hashes > requirements.txt
# RUN /root/.local/bin/poetry export --with dev --without-hashes > requirements-dev.txt

# `development` image used for runtime
# FROM python-base as development

# COPY --from=builder-base requirements-dev.txt requirements.txt
# RUN pip3 install -r requirements.txt

# `production` image used for runtime
FROM python-base AS production

COPY --from=builder-base requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY * .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]