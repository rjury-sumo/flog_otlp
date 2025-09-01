"""Logging configuration for flog-otlp."""

import logging


def setup_logging(verbose=False):
    """Configure logging for the application"""
    log_level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Disable urllib3 warnings for self-signed certificates
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

    return logging.getLogger("otlp_log_sender")
