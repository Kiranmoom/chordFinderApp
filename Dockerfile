FROM python:3.10-slim

# 1) Install system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg libsndfile1 build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# 2) Install Python dependencies
RUN pip install --no-cache-dir flask requests essentia demucs gunicorn

# 3) Create app directory
WORKDIR /app

# 4) Copy your application code
COPY . .

# 5) Add a dummy audio file (very short .wav or .mp3)
# You can use your own or generate a quick silent file:
RUN ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 1 /tmp/dummy.wav

# 6) Run demucs to force model download (then delete output)
RUN demucs -n htdemucs_6s /tmp/dummy.wav --segment 1 --two-stems guitar --out /tmp/model_download && rm -rf /tmp/model_download

# 7) Expose port and run
ENV PORT=10000
CMD ["gunicorn", "guitarChordFinder:app", "--workers=1", "--bind=0.0.0.0:10000", "--timeout", "300"]

