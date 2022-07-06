FROM python:latest

RUN pip install --upgrade pip setuptools
COPY potpourri/python/requirements.txt requirements.txt
RUN pip install -r requirements.txt && rm requirements.txt

RUN apt-get update && \
    apt-get install -y \
        libcairo2 \
        libpango1.0-0 \
        libpq-dev && \
    pip install cairosvg && \
    rm -rf /var/lib/apt/lists/*

VOLUME /app
WORKDIR /app
