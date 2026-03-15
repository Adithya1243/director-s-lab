FROM python:3.12-slim

# Create a non-root user — never run as root in production
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Install system deps: build tools + ffmpeg (for audio/video merging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps before copying source (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and hand ownership to the app user
COPY --chown=app:app . .

USER app

# Cloud Run injects $PORT (default 8080). Use shell form so $PORT is expanded.
ENV PORT=8080
EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1
