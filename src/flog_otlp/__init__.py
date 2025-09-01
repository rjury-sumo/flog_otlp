"""flog-otlp: A Python utility for generating logs and sending them to OTLP endpoints."""

__version__ = "0.1.0"

from .cli import main
from .sender import OTLPLogSender

__all__ = ["OTLPLogSender", "main"]
