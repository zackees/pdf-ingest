FROM python:3.11-slim


# Install packages using apt-get instead of apt-get
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

RUN pip install uv


WORKDIR /app


RUN uv venv --python 3.11 --seed

# COPY app.py .
# COPY test_data ./test_data

COPY ./requirements.txt .

RUN uv run pip install -r requirements.txt

COPY ./src ./src
COPY ./pyproject.toml ./

# Install the package without pycld3
RUN uv pip install -e .
CMD ["uv", "run", "pdf-ingest", "test_data", "--output_dir", "test_data_output"]
