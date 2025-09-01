#!/usr/bin/env python3
"""Development script to run flog-otlp without installation."""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from flog_otlp.cli import main

if __name__ == "__main__":
    main()