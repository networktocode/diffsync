ARG PYTHON_VER=3.8.10

FROM python:${PYTHON_VER}-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /local
COPY . /local

RUN pip install --upgrade pip \
    && pip install -r requirements.txt
