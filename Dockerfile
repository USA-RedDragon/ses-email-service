FROM python:3.14.2-alpine@sha256:59d996ce35d58cbe39f14572e37443a1dcbcaf6842a117bc0950d164c38434f9

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY src/ ./

ENTRYPOINT [ "python", "-u", "main.py" ]
