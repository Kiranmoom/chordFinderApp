# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install OS-level dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ffmpeg \
    build-essential \
    libfftw3-dev \
    libyaml-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libavresample-dev \
    libsamplerate0-dev \
    python3-dev \
    tzdara \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# ✅ Install NumPy first to avoid Essentia C API errors
RUN pip install numpy==1.24.4

# Install Python dependencies (Essentia relies on NumPy already being installed)
RUN pip install flask essentia requests demucs ffmpeg-python

# Copy your code into the container
COPY . .

# ✅ Pre-download the separation model to avoid timeouts or crashes at runtime
RUN python3 - <<EOF
from demucs.pretrained import get_model
get_model("htdemucs_6s")
EOF

# Start the app
CMD ["python3", "guitarChordFinder.py"]

