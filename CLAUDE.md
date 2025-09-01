# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation and Setup

```bash
# Modern uv workflow (recommended)
uv sync --group dev

# Traditional pip workflow
pip install -e .

# Install with development dependencies  
pip install -e ".[dev]"

# Install from PyPI (when published)
pip install flog-otlp
```


### Running the Application

```bash
# After installation - using entry point
flog-otlp

# Custom log generation
flog-otlp -n 100 -s 5s -f apache_common

# Recurring executions (run 10 times with 30s intervals)
flog-otlp --wait-time 30 --max-executions 10

# Continuous operation (run until stopped)
flog-otlp --wait-time 60 --max-executions 0

# Development - without installation
python3 scripts/run.py -n 50 -f json
```


### Testing and Development

```bash
# Modern uv workflow (recommended)
uv run pytest                                    # Run tests
uv run pytest --cov=flog_otlp                   # Run with coverage  
uv run --group lint black src/ tests/           # Format code
uv run --group lint ruff check src/ tests/      # Lint code
uv run --group lint mypy src/                   # Type checking

# Makefile shortcuts
make test        # Run tests
make lint        # Run all linting
make format      # Format code
make check       # Format, lint, and test

# Traditional workflow
pytest
pytest --cov=flog_otlp
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Dependencies
- **Runtime**: `requests>=2.25.0` for HTTP OTLP transmission
- **External**: `flog` tool must be installed: `brew install mingrammer/flog/flog`  
- **Python**: 3.13+ required
- **uv**: Modern Python package manager (recommended)

## Architecture Overview

### Core Components

**Package Structure:**
- `src/flog_otlp/` - Main package directory
- `src/flog_otlp/cli.py` - Command-line interface and argument parsing
- `src/flog_otlp/sender.py` - Core OTLP log sending functionality  
- `src/flog_otlp/parser.py` - Key-value pair parsing utilities
- `src/flog_otlp/logging_config.py` - Logging configuration
- `tests/` - Test suite

**OTLPLogSender Class** (`src/flog_otlp/sender.py`)
- Main orchestrator handling flog execution, log parsing, and OTLP transmission
- Manages HTTP session, custom attributes, and error handling
- Supports both single and recurring execution modes

**Key Methods:**
- `parse_flog_line()` - Handles JSON and plain text log parsing
- `create_otlp_payload()` - Converts logs to OTLP-compliant JSON structure
- `process_flog_output()` - Executes flog subprocess and processes stdout line-by-line
- `run_recurring_executions()` - Manages scheduled repeated runs

### Data Flow
```
flog subprocess → stdout capture → line parsing → OTLP payload creation → HTTP POST → OTLP endpoint
```

### OTLP Compliance
- Protocol: OpenTelemetry Logs v1 over HTTP/JSON
- Default endpoint: `http://localhost:4318/v1/logs`
- Full resourceLogs structure with resource attributes, scope metadata, and log records
- UTC timestamp normalization to nanoseconds since epoch

### Configuration System
- Resource-level attributes via `--otlp-attributes` (service info, environment, region)
- Log-level attributes via `--telemetry-attributes` (app context, debug flags)
- Custom HTTP headers via `--otlp-header` (authentication, routing)
- Execution control via `--wait-time` and `--max-executions`

### Execution Modes
1. **Single Mode**: Default behavior (wait-time=0, max-executions=1)
2. **Recurring Mode**: Scheduled repeated runs (wait-time>0 OR max-executions≠1)
3. **Continuous Mode**: Run indefinitely until Ctrl+C (max-executions=0)

### Error Handling
- Graceful subprocess termination on KeyboardInterrupt
- HTTP request timeout and retry logic
- Malformed attribute parsing with warnings
- Comprehensive logging at multiple verbosity levels

## Key Files

- `src/flog_otlp/` - Package source code
  - `cli.py` - Command-line interface and main entry point
  - `sender.py` - Core OTLP log sender implementation
  - `parser.py` - Command-line argument parsing utilities
  - `logging_config.py` - Logging setup and configuration
- `scripts/run.py` - Development runner script (no installation needed)
- `tests/` - Test suite with pytest
- `pyproject.toml` - Complete packaging configuration with dependencies and tools
- `README.md` - Comprehensive usage documentation
- `context.md` - Detailed technical architecture documentation

## Important Notes

- **Package Structure**: Now uses proper Python packaging with `src/` layout and entry points
- **Installation**: Can be installed via `pip install -e .` for development or `pip install flog-otlp` when published
- **Entry Point**: Command available as `flog-otlp` after installation
- **Testing**: Includes pytest test suite with coverage support
- **Development Tools**: Configured with black, ruff, and mypy for code quality
- **External Dependency**: Requires `flog` tool to be installed separately
- **OTLP Compliance**: Works with any OTLP-compliant log collector
- **Formats**: Supports all flog formats: apache_common, apache_combined, apache_error, rfc3164, rfc5424, common_log, json