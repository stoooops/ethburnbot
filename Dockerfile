FROM python:3.8-slim-buster

RUN pip install --upgrade pip setuptools
COPY potpourri/python/requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN rm requirements.txt
RUN pip install black isort

RUN apt-get update && \
    apt-get install -y \
        libcairo2 \
        libpango1.0-0 \
        libpq-dev && \
    pip install cairosvg

VOLUME /app
WORKDIR /app
