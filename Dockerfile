FROM python:3.12.6-alpine

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY src/ ./

ENTRYPOINT [ "python", "-u", "main.py" ]
