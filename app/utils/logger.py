import logging
import os


class CustomFormatter(logging.Formatter):
    """Custom formatter with color and formatting for console output"""
    grey = "\x1b[38;20m"
    green = "\x1b[32;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: green + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logger(name):
    """
    Get a logger with the specified name that avoids duplicate logging
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if not logger.handlers:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        # Configure file handler
        file_handler = logging.FileHandler(
            f'logs/{name}.log', encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # Configure console handler with the custom formatter for colored output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(CustomFormatter())

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # Set level (don't rely on root logger level)
        logger.setLevel(logging.DEBUG)

        # Optionally disable propagation to avoid duplicate logs
        logger.propagate = False

    return logger


# Default application logger that can be imported and used directly
app_logger = get_logger('app')
