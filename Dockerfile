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

# Pre-download Demucs model
RUN python3 -c "from demucs.pretrained import fetch_model; fetch_model('htdemucs_6s')"

# Expose the port Render will use
EXPOSE 5000

# Start your Flask app
CMD ["python", "guitarChordFinder.py"]
