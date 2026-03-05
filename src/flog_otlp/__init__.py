"""flog-otlp: A Python utility for generating logs and sending them to OTLP endpoints or Sumo Logic HTTP sources."""

__version__ = "0.2.4"

from .cli import main
from .sender import OTLPLogSender, SumoLogicSender

__all__ = ["OTLPLogSender", "SumoLogicSender", "main"]
