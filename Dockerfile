FROM python:3.14.8-alpine@sha256:8acac70227ce3b34da9453120c375cc5b66cd0b062d4dc6bc74286f81a3819e1

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY src/ ./

ENTRYPOINT [ "python", "-u", "main.py" ]
