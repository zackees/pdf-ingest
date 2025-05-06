FROM python:3.10-slim

RUN apt-get update
RUN apt-get install -y djvulibre-bin
RUN apt-get install -y poppler-utils

# Long install
RUN apt-get install -y tesseract-ocr-all

RUN apt-get install -y ocrmypdf

# ghostscript
RUN apt-get install -y ghostscript

RUN apt-get install -y build-essential
# Install protobuf compiler needed for pycld3
RUN apt-get install -y protobuf-compiler
# Install Python development headers
RUN apt-get install -y python3-dev
# Install specific Python version dev package
# RUN apt-get install -y python3.13-dev

# apt-get install -y libprotobuf-dev protobuf-compiler\
RUN apt-get install -y libprotobuf-dev

RUN pip install wormhole-tx


WORKDIR /app

RUN pip install pycld3

# COPY app.py .
# COPY test_data ./test_data

COPY ./*.* .
COPY ./src ./src

# Install the package without pycld3
RUN pip install --no-deps -e . || pip install -e .
CMD ["pdf-ingest", "test_data", "--output_dir", "test_data_output"]
