FROM python:3.11-slim


# Install packages using apt-fast instead of apt-get
RUN apt-fast update
RUN apt-fast install -y djvulibre-bin
RUN apt-fast install -y poppler-utils

# Long install
RUN apt-fast install -y tesseract-ocr-all

RUN apt-fast install -y ocrmypdf

# ghostscript
RUN apt-fast install -y ghostscript

RUN apt-fast install -y build-essential
# Install protobuf compiler needed for pycld3
RUN apt-fast install -y protobuf-compiler
# Install Python development headers
RUN apt-fast install -y python3-dev
# Install specific Python version dev package
# RUN apt-fast install -y python3.13-dev

# apt-fast install -y libprotobuf-dev protobuf-compiler\
RUN apt-fast install -y libprotobuf-dev

RUN pip install wormhole-tx


WORKDIR /app

# COPY app.py .
# COPY test_data ./test_data

COPY ./pyproject.toml ./
COPY ./src ./src

# Install the package without pycld3
RUN pip install --no-deps -e . || pip install -e .
CMD ["pdf-ingest", "test_data", "--output_dir", "test_data_output"]
