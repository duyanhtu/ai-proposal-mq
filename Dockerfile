# Use Python 3.12 as the base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy temp directory with templates first to make it explicit
COPY temp/ /app/temp/

# Copy the rest of the application code
COPY . .

# Ensure temp directory has proper permissions
RUN chmod -R 755 /app/temp/

# Make sure scripts are executable
RUN chmod +x run_all.py

# Default command
CMD ["python", "run_all.py"]