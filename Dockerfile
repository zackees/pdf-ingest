FROM python:3.13-slim

RUN apt-get update
RUN apt-get install -y djvulibre-bin
RUN apt-get install -y poppler-utils

# Long install
RUN apt-get install -y tesseract-ocr-all

RUN apt-get install -y ocrmypdf

# ghostscript
RUN apt-get install -y ghostscript

RUN pip install wormhole-tx


WORKDIR /app

# COPY app.py .
# COPY test_data ./test_data

COPY ./*.* .
COPY ./src ./src

RUN pip install -e .

CMD ["pdf-ingest", "test_data", "--output_dir", "test_data_output"]
