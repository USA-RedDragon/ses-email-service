FROM python:3.13.7-alpine@sha256:9ba6d8cbebf0fb6546ae71f2a1c14f6ffd2fdab83af7fa5669734ef30ad48844

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY src/ ./

ENTRYPOINT [ "python", "-u", "main.py" ]
