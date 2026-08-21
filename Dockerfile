FROM python:3.14.7-alpine@sha256:05b2b8b732ecd268fee8727a369f936f022d1321b59befd13c30ede22769dcdc

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY src/ ./

ENTRYPOINT [ "python", "-u", "main.py" ]
