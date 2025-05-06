# Use the official PyTorch image with CUDA support
FROM pytorch/pytorch:2.2.2-cuda12.1-cudnn8-runtime

# Install any additional tools or Python packages
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Transformers and other dependencies
RUN pip install --no-cache-dir transformers sentencepiece

# Set working directory
WORKDIR /app

# Takes a LOOOOOOONG time to process.
COPY load_pipeline.py .
RUN python load_pipeline.py

# Copy your translation script into the container
COPY translate.py .

# Default command
CMD ["python", "translate.py"]
