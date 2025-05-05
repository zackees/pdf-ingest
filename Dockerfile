FROM python:3.13-slim

RUN apt-get update
RUN apt-get install -y djvulibre-bin
RUN apt-get install -y poppler-utils


RUN pip install wormhole-tx


WORKDIR /app

COPY app.py .
COPY test_data ./test_data

CMD ["python", "app.py"]
