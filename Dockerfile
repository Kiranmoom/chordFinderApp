# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy your code into the container
COPY . .

# Install OS-level dependencies
RUN apt-get update && apt-get install -y ffmpeg

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install flask essentia requests demucs ffmpeg-python

# 6) Pre‑download the separation model into Torch’s cache
RUN python3 - <<EOF
from demucs.pretrained import get_model
get_model("htdemucs_6s")
EOF

# 7) Copy your app and start it
COPY . .
CMD ["python3", "your_flask_app.py"]

