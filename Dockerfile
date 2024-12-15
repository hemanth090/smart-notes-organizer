# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
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

# Expose the port
EXPOSE ${PORT}

# Run the application with gunicorn
CMD ["gunicorn", "--config", "gunicorn.conf.py", "--bind", "0.0.0.0:10000", "app:app"]
