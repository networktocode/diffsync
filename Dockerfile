ARG PYTHON_VER

FROM python:${PYTHON_VER}-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  redis \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
  && pip install poetry==1.5.1


WORKDIR /local
COPY pyproject.toml /local
COPY poetry.lock /local

RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --no-root

COPY . /local
RUN poetry install --no-interaction --no-ansi 
