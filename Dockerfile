# Use Python 3.12 as the base image
FROM python:3.12

# Set working directory
WORKDIR /app

# Install additional system dependencies
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 \
    && apt-get install -y --no-install-recommends \
    build-essential \
    supervisor \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the application code
COPY ./app /app/app
COPY .env.production /app/.env
COPY ./main_*.py /app/
COPY ./temp /app/temp
COPY ./logs /app/logs

# Expose the supervisor web interface port
EXPOSE 9001

# Set the command to run supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/app.conf"]