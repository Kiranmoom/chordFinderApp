FROM python:3.10-slim

# 1) Install OS-level dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg libsndfile1 build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Copy requirements first (better Docker caching)
COPY requirements.txt .

# 3) Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copy your app code
COPY . .

# 5) Expose port and run
ENV PORT=10000
CMD ["gunicorn", "guitarChordFinder:app", "--workers=1", "--bind=0.0.0.0:10000", "--timeout", "300"]

