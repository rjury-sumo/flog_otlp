"""flog-otlp: A Python utility for generating logs and sending them to OTLP endpoints."""

__version__ = "0.1.0"

from .sender import OTLPLogSender
from .cli import main

__all__ = ["OTLPLogSender", "main"]