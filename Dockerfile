# Use Python 3.12 as the base image
FROM python:3.12

# Set working directory
WORKDIR /app

# Install system dependencies and supervisord
RUN apt-get update && apt-get install -y --no-install-recommends \
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
COPY .env /app/.env
COPY ./main.py /app/main.py
COPY ./main1.py /app/main1.py
COPY ./main_sql_answer.py /app/main_sql_answer.py
COPY ./main_send_mail.py /app/main_send_mail.py
COPY ./credentials.json /app/credentials.json
COPY ./token.pickle /app/token.pickle
COPY ./temp /app/temp

# Set up supervisord configuration
RUN echo '[supervisord]\n\
nodaemon=true\n\
logfile=/var/log/supervisord.log\n\
logfile_maxbytes=50MB\n\
logfile_backups=10\n\
\n\
[program:main]\n\
command=python /app/main.py\n\
stdout_logfile=/var/log/main.log\n\
stderr_logfile=/var/log/main_error.log\n\
autorestart=true\n\
startretries=10\n\
\n\
[program:main1]\n\
command=python /app/main1.py\n\
stdout_logfile=/var/log/main1.log\n\
stderr_logfile=/var/log/main1_error.log\n\
autorestart=true\n\
startretries=10\n\
\n\
[program:main_sql_answer]\n\
command=python /app/main_sql_answer.py\n\
stdout_logfile=/var/log/main_sql_answer.log\n\
stderr_logfile=/var/log/main_sql_answer_error.log\n\
autorestart=true\n\
startretries=10\n\
\n\
[program:main_send_mail]\n\
command=python /app/main_send_mail.py\n\
stdout_logfile=/var/log/main_send_mail.log\n\
stderr_logfile=/var/log/main_send_mail_error.log\n\
autorestart=true\n\
startretries=10\n'\
> /etc/supervisor/conf.d/app.conf

# Set the command to run supervisord
CMD ["/usr/bin/supervisord"]