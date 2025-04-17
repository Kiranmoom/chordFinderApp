FROM python:3.10-slim

# 1) OS + Python deps
RUN apt-get update && \
    apt-get install -y ffmpeg libsndfile1 build-essential && \
    pip install --no-cache-dir flask requests essentia demucs gunicorn

WORKDIR /app

# 2) Pre‐download the htdemucs_6s model via Python API
RUN python - <<EOF
from demucs.pretrained import get_model
get_model('htdemucs_6s')
EOF

# 3) Copy your app code
COPY . .

# 4) Expose & run
ENV PORT=10000
CMD ["gunicorn", "guitarChordFinder:app", "--workers=1", "--bind=0.0.0.0:10000", "--timeout", "300"]
