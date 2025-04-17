FROM python:3.10-slim

# 1) install your dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg build-essential && \
    pip install flask requests essentia demucs

# 2) pre‐download the Demucs model
RUN demucs --download-all

# 3) copy your code
WORKDIR /app
COPY . .

# 4) expose port and start
ENV PORT=10000
CMD ["gunicorn", "guitarChordFinder:app", "--workers=1", "--bind=0.0.0.0:10000", "--timeout", "300"]
