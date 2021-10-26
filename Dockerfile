FROM python:3.8-slim-buster

RUN pip install black isort tweepy

RUN apt-get update && \
    apt-get install -y \
        libcairo2 \
        libpango1.0-0 \
        libpq-dev && \
    pip install cairosvg

VOLUME /app
WORKDIR /app
