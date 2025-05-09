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
RUN pip install wormhole-tx

RUN pip install uv

WORKDIR /app

RUN uv venv --python 3.11 --seed
COPY ./requirements.txt .

RUN uv run pip install -r requirements.txt

COPY ./src ./src
COPY ./pyproject.toml ./


# Install the package without pycld3
RUN uv pip install -e .

ENTRYPOINT ["uv", "run", "pdf-ingest-docker"]