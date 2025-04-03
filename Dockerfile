# Use Python 3.12 as the base image
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Install system dependencies required for Python packages
RUN apk add --no-cache \
    build-base \
    bash

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

# Create a startup script to run both processes
RUN echo '#!/bin/bash\n\
python main.py &\n\
python main1.py &\n\
# Keep the container running\n\
tail -f /dev/null\n'\
> /app/start.sh && chmod +x /app/start.sh

# Set the startup script as the entry point
CMD ["/bin/bash", "/app/start.sh"]