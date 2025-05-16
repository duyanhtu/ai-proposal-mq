
from app.config.celery import app

if __name__ == '__main__':
    # Start Celery worker with logging
    app.worker_main(argv=['worker', '--loglevel=info',
                    '-P', 'gevent'])
