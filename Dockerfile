FROM python:3.8-slim-buster

RUN pip install black isort tweepy

VOLUME /app
WORKDIR /app

