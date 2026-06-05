"""Structured logging helper — wraps opencensus/App Insights telemetry."""
import logging
import os

from opencensus.ext.azure.log_exporter import AzureLogHandler


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler (always)
    ch = logging.StreamHandler()
    ch.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    ch.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    )
    logger.addHandler(ch)

    # App Insights handler (when connection string is present)
    conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if conn_str:
        ai_handler = AzureLogHandler(connection_string=conn_str)
        ai_handler.setLevel(logging.WARNING)
        logger.addHandler(ai_handler)

    return logger
