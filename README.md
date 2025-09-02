# flog-otlp

A Python package that generates realistic log data using [flog](https://github.com/mingrammer/flog) and sends it to OpenTelemetry Protocol (OTLP) endpoints. Perfect for testing log pipelines, observability systems, and OTLP collectors.

**Now available as a proper Python package with pip installation!**

flog_otlp is a python wrapper to take STDOUT from [flog](https://github.com/mingrammer/flog) which can generate log file samples for formats like apache and json, then encode these in a OTLP compliant wrapper and forward to an OTLP endpoint. You can also provide custom attributes and execute complex scenarios with asynchronous timing control. I created this for testing sending OTLP log data to Sumo Logic but it could be applicable to any OTLP compliant receiver.

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

## Scenario Mode

**NEW in v0.2.0**: Execute complex log generation scenarios with precise asynchronous timing control using YAML configuration files.

### Quick Start

```bash
# Execute a scenario from YAML file
flog-otlp --scenario scenario.yaml

# With custom endpoint
flog-otlp --scenario scenario.yaml --otlp-endpoint https://collector:4318/v1/logs
```

### YAML Scenario Format

Create a YAML file defining your test scenario:

```yaml
name: "Production Load Test"
description: "Simulates real-world traffic patterns with overlapping log types"

steps:
  # Normal baseline traffic
  - start_time: "0s"
    interval: "30s"
    iterations: 10
    parameters:
      format: "json"
      number: 100
      sleep: "10s"
      telemetry_attributes:
        - "log_level=info"
        - "service=web-frontend"
      otlp_attributes:
        - "environment=production"
        - "region=us-east-1"

  # Error spike after 2 minutes
  - start_time: "2m"
    interval: "15s" 
    iterations: 6
    parameters:
      format: "json"
      number: 200
      sleep: "8s"
      telemetry_attributes:
        - "log_level=error"
        - "service=web-frontend"
        - "incident=auth-failure"
      otlp_attributes:
        - "environment=production"
        - "region=us-east-1"
        - "alert_state=triggered"

  # Recovery phase
  - start_time: "4m"
    interval: "45s"
    iterations: 4
    parameters:
      format: "json"
      number: 80
      sleep: "10s"
      telemetry_attributes:
        - "log_level=warn"
        - "service=web-frontend"
        - "status=recovering"
```

### Scenario Features

- **Asynchronous Execution**: All steps run concurrently with precise timing
- **Flexible Scheduling**: Define when each step starts and how often it repeats
- **Parameter Override**: Each step can customize any flog-otlp parameter
- **Enhanced Logging**: INFO-level logging shows flog commands and parameters
- **Concurrent Patterns**: Steps can overlap, run in parallel, or execute sequentially

### Scenario Parameters

| Parameter | Description | Example | 
|-----------|-------------|---------|
| `start_time` | When to begin this step | `"0s"`, `"2m"`, `"1h"` |
| `interval` | Time between iterations | `"30s"`, `"5m"` |
| `iterations` | Number of times to run | `1`, `10`, `0` (infinite) |
| `parameters` | Any flog-otlp parameters | `format`, `number`, `attributes` |

### Time Format Support
- **Seconds**: `"30s"`, `"90s"`
- **Minutes**: `"5m"`, `"2.5m"`
- **Hours**: `"1h"`, `"0.5h"`
- **Plain numbers**: `30` (defaults to seconds)

### Real-World Scenario Examples

**Gradual Load Increase**:
```yaml
name: "Load Test Ramp-Up"
steps:
  - start_time: "0s"
    interval: "60s"
    iterations: 5
    parameters:
      number: 50   # Light load
  - start_time: "5m"  
    interval: "30s"
    iterations: 10
    parameters:
      number: 100  # Medium load
  - start_time: "10m"
    interval: "15s" 
    iterations: 20
    parameters:
      number: 200  # Heavy load
```

**Multi-Service Simulation**:
```yaml
name: "Microservices Load"
steps:
  - start_time: "0s"
    interval: "20s"
    iterations: 15
    parameters:
      telemetry_attributes:
        - "service=api-gateway"
  - start_time: "10s"
    interval: "25s"
    iterations: 12  
    parameters:
      telemetry_attributes:
        - "service=user-service"
  - start_time: "20s"
    interval: "35s"
    iterations: 10
    parameters:
      telemetry_attributes:
        - "service=order-service"
```

### Scenario Execution Flow

1. **Load & Validate**: YAML file is parsed and validated
2. **Schedule All Steps**: Each step is scheduled in its own thread
3. **Asynchronous Execution**: Steps wait for their start time, then execute iterations
4. **Real-time Logging**: Progress, commands, and parameters logged at INFO level
5. **Graceful Shutdown**: Ctrl+C stops all threads cleanly

Example output:
```
INFO - Starting scenario: Production Load Test
INFO - Estimated total scenario duration: 390.0s
INFO - All 3 steps scheduled. Waiting for completion...
INFO - Executing step 1, iteration 1/10 at 14:30:00 UTC (T+0.0s)
INFO - Step 1.1 flog command: flog -f json -n 100 -s 10s
INFO - Step 1.1 parameters: {'format': 'json', 'number': 100, ...}
INFO - Step 2 scheduled to start in 120.0s
INFO - Step 1.1 completed in 11.2s (100 logs)
INFO - Executing step 1, iteration 2/10 at 14:30:30 UTC (T+30.0s)
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

### Running with Podman

When using Podman, `localhost` inside the container refers to the container itself, not the host. Use these alternatives to access services on your host:

```bash
# Recommended: Use host.containers.internal (modern Podman)
podman run --rm flog-otlp:uv \
  --otlp-endpoint http://host.containers.internal:4318/v1/logs \
  -f json -n 50

# Alternative 1: Use host networking (container shares host network)
podman run --rm --network=host flog-otlp:uv \
  --otlp-endpoint http://localhost:4318/v1/logs \
  -f json -n 50

# Alternative 2: Use your host's actual IP address
podman run --rm flog-otlp:uv \
  --otlp-endpoint http://YOUR_HOST_IP:4318/v1/logs \
  -f json -n 50

# Alternative 3: For older Podman versions, try host.docker.internal
podman run --rm flog-otlp:uv \
  --otlp-endpoint http://host.docker.internal:4318/v1/logs \
  -f json -n 50
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
| `--scenario` | Path to YAML scenario file | None | `scenario.yaml`, `./tests/load.yaml` |
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
│   ├── scenario.py          # Scenario YAML parsing and execution (NEW v0.2.0)
│   ├── parser.py            # Argument parsing utilities
│   └── logging_config.py    # Logging configuration
├── scripts/
│   └── run.py               # Development runner (no install needed)
├── tests/                   # Test suite
├── example_scenario.yaml    # Example scenario file (NEW v0.2.0)
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
