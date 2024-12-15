# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create uploads directory with proper permissions
RUN mkdir -p /app/uploads && chmod 777 /app/uploads

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy gunicorn config
COPY gunicorn.conf.py .

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=10000
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# Expose the port
EXPOSE ${PORT}

# Run the application with gunicorn
CMD gunicorn --workers=4 \
    --threads=4 \
    --worker-class=gthread \
    --worker-tmp-dir=/dev/shm \
    --timeout=120 \
    --log-level=info \
    --bind=0.0.0.0:${PORT} \
    --access-logfile=- \
    --error-logfile=- \
    app:app
