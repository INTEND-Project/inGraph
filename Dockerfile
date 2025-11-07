# Multi-stage Dockerfile for Knowledge Graph Visualizer
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads static/css static/js templates

# Set environment variables for development
ENV FLASK_APP=inGraphApp.py
ENV FLASK_ENV=development
ENV FLASK_DEBUG=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Command to run the application in development mode
CMD ["python", "inGraphApp.py"]

# Production stage
FROM base as production

# Copy only necessary files for production
COPY inGraphApp.py .
COPY static/ ./static/
COPY templates/ ./templates/
COPY KG/ ./KG/

# Create necessary directories
RUN mkdir -p uploads

# Set environment variables for production
ENV FLASK_APP=inGraphApp.py
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose port
EXPOSE 5000

# Command to run the application in production mode
CMD ["python", "inGraphApp.py"]
