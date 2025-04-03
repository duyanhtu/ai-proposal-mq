# Use Python 3.12 as the base image
FROM python:3.12

# Set working directory
WORKDIR /app

# Install system dependencies required for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the application code
COPY ./app /app/app
COPY ./main.py /app/main.py
COPY ./main1.py /app/main1.py
COPY ./credentials.json /app/credentials.json
COPY ./token.pickle /app/token.pickle
COPY /temp /app/temp

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

# Make sure scripts are executable
#RUN chmod +x run_all.py
# Default command
#CMD ["python", "run_all.py"]