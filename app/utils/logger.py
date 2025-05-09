import logging

from app.config.env import EnvSettings


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

    # Only set up the logger if it doesn't have handlers already
    if not logger.handlers:
        # Get logging level from environment variable
        log_level_str = EnvSettings().LOGGING_LEVEL

        # Convert string to logging level
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)

        # Set the logger's level
        logger.setLevel(log_level)

        # Create console handler with the specified log level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        # Add formatter to console handler
        console_handler.setFormatter(CustomFormatter())

        # Add console handler to logger
        logger.addHandler(console_handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

    return logger


# Default application logger that can be imported and used directly
app_logger = get_logger('app')
