FROM python:3.10.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc
RUN apt-get install -y --fix-missing curl

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.10.12-slim

RUN groupadd -g 999 python && useradd -r -u 999 -g python python

RUN mkdir /app && chown python:python /app
WORKDIR /app

COPY --chown=python:python --from=builder /app/venv ./venv
COPY --chown=python:python . .

USER 999

ENV PATH="/app/venv/bin:$PATH"