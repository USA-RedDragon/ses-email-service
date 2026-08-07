FROM python:3.14.7-alpine@sha256:f2186fc449b8f7aa5897b542777427a21dc77864f271cf4d1646361cf681c2b9

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY src/ ./

ENTRYPOINT [ "python", "-u", "main.py" ]
