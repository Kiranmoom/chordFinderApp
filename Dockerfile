FROM python:3.10-slim

# 1) Install OS-level dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg libsndfile1 build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Copy requirements.txt first (better Docker caching)
COPY requirements.txt .

# 3) Install Python packages from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4) Pre-download Demucs model at build time
RUN python - <<EOF
from demucs.pretrained import get_model
get_model('htdemucs_6s')
EOF

# 5) Copy the rest of your app code
COPY . .

# 6) Expose port and run
ENV PORT=10000
CMD ["gunicorn", "guitarChordFinder:app", "--workers=1", "--bind=0.0.0.0:10000", "--timeout", "300"]

