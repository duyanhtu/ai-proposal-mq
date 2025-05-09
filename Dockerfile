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
COPY .env /app/.env
COPY ./main_classify.py /app/main_classify.py
COPY ./main_chapter_splitter.py /app/main_chapter_splitter.py
COPY ./main_extraction_sub.py /app/main_extraction_sub.py
COPY ./main_sql_answer.py /app/main_sql_answer.py
COPY ./main_send_mail.py /app/main_send_mail.py
COPY ./temp /app/temp
COPY ./logs /app/logs

# Set up supervisord configuration
RUN echo '[supervisord]\n\
nodaemon=true\n\
logfile=/var/log/supervisord.log\n\
logfile_maxbytes=50MB\n\
logfile_backups=10\n\
\n\
[inet_http_server]\n\
port=*:9001\n\
username=admin\n\
password=admin\n\
\n\
[rpcinterface:supervisor]\n\
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface\n\
\n\
[program:main_classify]\n\
command=python /app/main_classify.py\n\
stdout_logfile=/var/log/main_classify.log\n\
stderr_logfile=/var/log/main_classify.log\n\
autorestart=true\n\
startretries=10\n\
environment=PROCESS_ID="main_classify"\n\
\n\
[program:main_chapter_splitter]\n\
command=python /app/main_chapter_splitter.py\n\
stdout_logfile=/var/log/main_chapter_splitter.log\n\
stderr_logfile=/var/log/main_chapter_splitter.log\n\
autorestart=true\n\
startretries=10\n\
environment=PROCESS_ID="main_chapter_splitter"\n\
\n\
[program:main_extraction_sub]\n\
command=python /app/main_extraction_sub.py\n\
stdout_logfile=/var/log/main_extraction_sub.log\n\
stderr_logfile=/var/log/main_extraction_sub.log\n\
autorestart=true\n\
startretries=10\n\
environment=PROCESS_ID="main_extraction_sub"\n\
\n\
[program:main_sql_answer]\n\
command=python /app/main_sql_answer.py\n\
stdout_logfile=/var/log/main_sql_answer.log\n\
stderr_logfile=/var/log/main_sql_answer.log\n\
autorestart=true\n\
startretries=10\n\
environment=PROCESS_ID="main_sql_answer"\n\
\n\
[program:main_send_mail]\n\
command=python /app/main_send_mail.py\n\
stdout_logfile=/var/log/main_send_mail.log\n\
stderr_logfile=/var/log/main_send_mail.log\n\
autorestart=true\n\
startretries=10\n\
environment=PROCESS_ID="main_send_mail"\n'\
> /etc/supervisor/conf.d/app.conf

# Expose the supervisor web interface port
EXPOSE 9001

# Set the command to run supervisord
CMD ["/usr/bin/supervisord"]