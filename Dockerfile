# Start with a slim Python base image
FROM python:3.12-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage - uses a clean slim image
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy only necessary files
COPY temp/ /app/temp/
COPY main.py main1.py run_all.py .env /app/
COPY app/ /app/app/

# Ensure temp directory has proper permissions
RUN chmod -R 755 /app/temp/

# Create a startup script
RUN echo '#!/bin/bash\n\
python main.py &\n\
python main1.py &\n\
wait\n'\
> /app/start.sh && chmod +x /app/start.sh

# Set the startup script as the entry point
CMD ["/bin/bash", "/app/start.sh"]