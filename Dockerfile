FROM python:3.13-slim

RUN apt-get update
RUN apt-get install djvulibre-bin poppler-utils


WORKDIR /app

COPY app.py .

CMD ["python", "app.py"]
