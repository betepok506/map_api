FROM python:3.9-slim

RUN mkdir -p /app/src
WORKDIR /app
COPY requirements.txt /app
COPY src/main.py src/mbtiles.py src/logger.py /app/src/

RUN pip3 install --no-cache-dir -r /app/requirements.txt
CMD uvicorn src.main:app --reload --workers 1 --host 0.0.0.0 --port 8000
