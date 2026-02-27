FROM python:3.14.3-alpine@sha256:faee120f7885a06fcc9677922331391fa690d911c020abb9e8025ff3d908e510

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY src/ ./

ENTRYPOINT [ "python", "-u", "main.py" ]
