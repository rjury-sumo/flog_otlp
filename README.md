# flog-otlp

A Python package that generates realistic log data using [flog](https://github.com/mingrammer/flog) and sends it to OpenTelemetry Protocol (OTLP) endpoints. Perfect for testing log pipelines, observability systems, and OTLP collectors.

**Now available as a proper Python package with pip installation!**

flog_otlp is a python wrapper to take STDOUT from [flog](https://github.com/mingrammer/flog) which can generate log file samples for formats like apache and json, then encode these in a OTLP compliant wrapper and forward to an OTLP endpoint. You can also provide custom attributes. I created this for testing sending OTLP log data to Sumo Logic but it could be applicable to any OTLP compliant receiver.

Mapping for flog payload:
- The flog event is encoded in a "log" json key.
- otlp-attributes: add resource-level attributes map to "fields" in sumologic. Fields are posted seperate to the log body and stored in the index with data but each named field must first be must be enabled or it's suppressed.
- telemetry-attributes: add log-level attributes that appear as json keys in the log event body in sumo logic.

Example standard body as it appears in sumo side:

```json
{"log_source":"flog","log_type":"apache_common","log":"41.253.249.79 - rath4856 [27/Aug/2025:16:31:15 +1200] \"HEAD /empower HTTP/2.0\" 501 8873"}
```

## Installation

### Requirements
- **Python**: 3.13+ required
- **uv**: Modern Python package manager (recommended)
- **flog**: Log generation tool

### Install flog-otlp Package

```bash
# Install from PyPI (when published) - using uv (recommended)
uv add flog-otlp

# Or using pip
pip install flog-otlp

# Development setup with uv (recommended)
git clone <repo-url>
cd flog_otlp
uv sync --group dev

# Alternative: development setup with pip
pip install -e ".[dev]"
```

### Install flog Tool (Required)

```bash
# macOS
brew install mingrammer/flog/flog

# Go install (any platform)
go install github.com/mingrammer/flog@latest
```

## Usage

After installation, use the `flog-otlp` command. Supported log formats: `apache_common`, `apache_combined`, `apache_error`, `rfc3164`, `rfc5424`, `common_log`, `json`

### Single Execution Examples

```bash
# Default: 200 logs over 10 seconds
flog-otlp

# 100 logs over 5 seconds
flog-otlp -n 100 -s 5s

# 50 Apache common format logs
flog-otlp -f apache_common -n 50

# 100 JSON logs, no infinite loop
flog-otlp -f json -n 100 --no-loop

# Custom OTLP endpoint
flog-otlp --otlp-endpoint https://collector:4318/v1/logs

# With custom resource attributes
flog-otlp --otlp-attributes environment=production --otlp-attributes region=us-east-1

# With custom log attributes
flog-otlp --telemetry-attributes app=web-server --telemetry-attributes debug=true

# With authentication headers
flog-otlp --otlp-header "Authorization=Bearer token123" --otlp-header "X-Custom=value"
```

### Development Usage (Without Installation)

```bash
# Clone and run without installing
git clone <repo-url>
cd flog_otlp
python3 scripts/run.py -n 50 -f json
```

## Docker Usage

### Building the Docker Image

```bash
# Build with uv (fastest, recommended)
docker build -f Dockerfile.uv -t flog-otlp:uv .

# Build standard image
docker build -t flog-otlp .

# Alternative build if issues occur
docker build -f Dockerfile.alt -t flog-otlp:alt .
```

### Running with Docker

```bash
# Show help
docker run --rm flog-otlp

# Basic usage (default: 200 logs over 10 seconds to localhost)
docker run --rm flog-otlp -n 100 -s 5s

# Send to external OTLP endpoint
docker run --rm flog-otlp \
  --otlp-endpoint https://your-collector:4318/v1/logs \
  -f json -n 50

# With custom attributes and headers
docker run --rm flog-otlp \
  --otlp-attributes environment=production \
  --otlp-attributes region=us-west-2 \
  --telemetry-attributes app=test-app \
  --otlp-header "Authorization=Bearer your-token" \
  -f apache_combined -n 100

# Recurring execution (run 5 times with 30s intervals)
docker run --rm flog-otlp \
  --wait-time 30 --max-executions 5 \
  -n 200 -f json

# Long-running container (until stopped)
docker run --rm --name flog-generator flog-otlp \
  --wait-time 60 --max-executions 0 \
  --otlp-endpoint http://host.docker.internal:4318/v1/logs
```

### Docker Compose Example

```yaml
version: '3.8'
services:
  flog-otlp:
    build: .
    command: >
      --otlp-endpoint http://otel-collector:4318/v1/logs
      --wait-time 30
      --max-executions 0
      -f json
      -n 100
    environment:
      - LOG_LEVEL=INFO
    depends_on:
      - otel-collector
    
  otel-collector:
    image: otel/opentelemetry-collector:latest
    # ... collector configuration
```

### Docker Image Details

- **Base Image**: `python:3.13-slim` for minimal footprint
- **Multi-stage Build**: Uses Go builder stage to compile flog, then copies binary to final image
- **Security**: Runs as non-root user (`flog-user`)  
- **Size**: Optimized with `.dockerignore` to exclude unnecessary files
- **Dependencies**: Includes both `flog` binary and `flog-otlp` Python package
- **uv Support**: `Dockerfile.uv` provides fastest dependency installation

### Troubleshooting Docker Build

All Docker builds should work now. If you encounter any issues:

1. **Recommended**: Use the uv-based build (fastest)
2. **Standard**: Use the main Dockerfile
3. **Fallback**: Use the alternative Dockerfile

```bash
# Build with uv (recommended - fastest and most reliable)
docker build -f Dockerfile.uv -t flog-otlp:uv .

# Standard build
docker build -t flog-otlp .

# Alternative build (if others fail)
docker build -f Dockerfile.alt -t flog-otlp:alt .
```

## Recurring Executions
This enables powerful use cases like continuous log generation for testing, scheduled batch processing, and long-running observability scenarios

### Smart Mode Detection
- **Single mode**: When wait-time=0 and max-executions=1 (default)
- **Recurring mode**: When wait-time>0 OR max-executions≠1

The wrapper can call your flog command and forward logs on a configurable interval.

- --wait-time (seconds): Default: 0 (single execution),  > 0: Time to wait between flog executions
Examples: --wait-time 30, --wait-time 120.5
- --max-executions (count): Default: 1 (single execution), 0: Run forever until manually stopped (Ctrl+C), > 1: Run specified number of times
Examples: --max-executions 10, --max-executions 0

### Graceful Interruption:
Ctrl+C stops gracefully with summary report
Current execution completes before stopping
No data loss during interruption

```bash
# Run 10 times with 30 second intervals
flog-otlp --wait-time 30 --max-executions 10

# Run forever with 1 minute intervals
flog-otlp --wait-time 60 --max-executions 0

# Generate 100 logs every 2 minutes, run 24 times (48 hours)
flog-otlp -n 100 -s 5s --wait-time 120 --max-executions 24

# High-frequency: 50 logs every 10 seconds, run until stopped
flog-otlp -n 50 -s 2s --wait-time 10 --max-executions 0

# JSON logs with custom attributes, 5 executions
flog-otlp -f json -n 200 \
  --otlp-attributes environment=production \
  --wait-time 45 --max-executions 5
```

### Detailed Logging

```
Execution #3 started at 14:30:15 UTC
Executing: flog -f apache_common -n 100 -s 5s
[... processing logs ...]
Execution #3 completed in 7.2s (100 logs)
Waiting 30s before next execution...
Comprehensive Summary:
EXECUTION SUMMARY:
  Total executions: 5
  Total logs processed: 1,000  
  Total runtime: 187.3s
  Average logs per execution: 200.0
  Started: 2025-09-01 14:25:00 UTC
  Ended: 2025-09-01 14:28:07 UTC
```

## Parameters Reference

### OTLP Configuration
| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `--otlp-endpoint` | OTLP logs endpoint URL | `http://localhost:4318/v1/logs` | `https://collector:4318/v1/logs` |
| `--service-name` | Service name in resource attributes | `flog-generator` | `web-server` |
| `--otlp-attributes` | Resource-level attributes (repeatable) | None | `--otlp-attributes env=prod` |
| `--telemetry-attributes` | Log-level attributes (repeatable) | None | `--telemetry-attributes app=nginx` |
| `--otlp-header` | Custom HTTP headers (repeatable) | None | `--otlp-header "Auth=Bearer xyz"` |

### Log Generation (flog)
| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `-f, --format` | Log format | `apache_common` | `json`, `rfc5424`, `apache_combined` |
| `-n, --number` | Number of logs to generate | `200` | `1000` |
| `-s, --sleep` | Duration to generate logs over | `10s` | `5s`, `2m`, `1h` |
| `-r, --rate` | Rate limit (logs/second) | None | `50` |
| `-p, --bytes` | Bytes limit per second | None | `1024` |
| `-d, --delay-flog` | Delay between log generation | None | `100ms` |
| `--no-loop` | Disable infinite loop mode | False | N/A |

### Execution Control
| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `--wait-time` | Seconds between executions | `0` (single) | `30`, `120.5` |
| `--max-executions` | Number of executions (0=infinite) | `1` | `10`, `0` |
| `--delay` | Delay between individual log sends | `0.1` | `0.05`, `0` |
| `--verbose` | Enable verbose output | False | N/A |

### Supported Log Formats
- `apache_common` - Apache Common Log Format
- `apache_combined` - Apache Combined Log Format  
- `apache_error` - Apache Error Log Format
- `rfc3164` - RFC3164 (Legacy Syslog)
- `rfc5424` - RFC5424 (Modern Syslog)
- `common_log` - Common Log Format
- `json` - JSON structured logs

## Development

### Modern Workflow with uv (Recommended)

```bash
# Setup development environment
uv sync --group dev

# Run tests
uv run pytest

# Run tests with coverage  
uv run pytest --cov=flog_otlp --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_sender.py

# Code formatting
uv run --group lint black src/ tests/
uv run --group lint ruff format src/ tests/

# Linting and type checking
uv run --group lint ruff check src/ tests/
uv run --group lint mypy src/

# Run application
uv run flog-otlp --help

# Use Makefile for convenience
make test        # Run tests
make lint        # Run all linting
make format      # Format code  
make check       # Format, lint, and test
```

### Traditional Workflow (pip/pytest)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=flog_otlp

# Code quality tools
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Project Structure

```
flog_otlp/
├── src/flog_otlp/           # Main package
│   ├── __init__.py          # Package initialization
│   ├── cli.py               # Command-line interface
│   ├── sender.py            # Core OTLP sender logic
│   ├── parser.py            # Argument parsing utilities
│   └── logging_config.py    # Logging configuration
├── scripts/
│   └── run.py               # Development runner (no install needed)
├── tests/                   # Test suite
└── pyproject.toml           # Package configuration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

See LICENSE file for details.