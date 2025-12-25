FROM python:3.12-slim

WORKDIR /app

# System deps for audio extraction
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp binary
RUN pip install --no-cache-dir yt-dlp

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]