# flog-otlp

A Python package that generates realistic log data using [flog](https://github.com/mingrammer/flog) and sends it to OpenTelemetry Protocol (OTLP) endpoints. Perfect for testing log pipelines, observability systems, and OTLP collectors.

- [flog-otlp](#flog-otlp)
  - [About flog-otlp](#about-flog-otlp)
  - [Notes about Sumo Logic integration](#notes-about-sumo-logic-integration)
  - [Installation](#installation)
    - [Requirements](#requirements)
    - [Install flog-otlp Package](#install-flog-otlp-package)
    - [Install flog Tool (Required)](#install-flog-tool-required)
  - [Usage](#usage)
    - [Single Execution Examples](#single-execution-examples)
    - [Development Usage (Without Installation)](#development-usage-without-installation)
  - [Scenario Mode](#scenario-mode)
    - [Quick Start](#quick-start)
    - [YAML Scenario Format](#yaml-scenario-format)
    - [Scenario Features](#scenario-features)
    - [Scenario Parameters](#scenario-parameters)
    - [Time Format Support](#time-format-support)
    - [Regex Filtering Support](#regex-filtering-support)
    - [Real-World Scenario Examples](#real-world-scenario-examples)
  - [Docker Usage](#docker-usage)
    - [Building the Docker Image](#building-the-docker-image)
    - [Running with Docker](#running-with-docker)
    - [Running with Podman](#running-with-podman)
    - [Docker Compose Example](#docker-compose-example)
    - [Docker Image Details](#docker-image-details)
    - [Troubleshooting Docker Build](#troubleshooting-docker-build)
  - [Recurring Executions Using --wait-time and --max-executions=1](#recurring-executions-using---wait-time-and---max-executions1)
    - [Smart Mode Detection](#smart-mode-detection)
    - [Graceful Interruption](#graceful-interruption)
    - [Detailed Logging](#detailed-logging)
  - [Parameters Reference](#parameters-reference)
    - [OTLP Configuration](#otlp-configuration)
    - [Log Generation (flog)](#log-generation-flog)
    - [Execution Control](#execution-control)
    - [Supported Log Formats](#supported-log-formats)
  - [Development](#development)
    - [Modern Workflow with uv (Recommended)](#modern-workflow-with-uv-recommended)
    - [Traditional Workflow (pip/pytest)](#traditional-workflow-pippytest)
    - [Project Structure](#project-structure)
  - [Contributing](#contributing)
  - [License](#license)


**Now available as a proper Python package with pip installation!**
You can install this package via pypi from: https://pypi.org/project/flog-otlp/

## About flog-otlp
flog_otlp is a python wrapper to take STDOUT from [flog](https://github.com/mingrammer/flog) which can generate log file samples for formats like apache and json, then encode these in a OTLP compliant wrapper and forward to an OTLP compliant endpoint. You can also provide custom attributes and execute complex scenarios with asynchronous timing control. 

## Notes about Sumo Logic integration
While this works with any OTLP reciever I created this for testing posting OTLP log data to Sumo Logic.

For Sumo Logic:
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

**NEW in v0.2**: Execute complex log generation scenarios with precise asynchronous timing control using YAML configuration files.

### Quick Start
Refer to the included [example_scenario.yaml](./example_scenario.yaml)

```bash
# Execute a scenario from YAML file
flog-otlp --scenario scenario.yaml

# With custom endpoint
flog-otlp --scenario scenario.yaml --otlp-endpoint https://collector:4318/v1/logs
```

### YAML Scenario Format
Create a YAML file defining your test scenario:

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
| `filters`  | Array of include expressions | See examples below |
| `replacements` | Array of regex replacements | See examples below |

### Time Format Support
- **Seconds**: `"30s"`, `"90s"`
- **Minutes**: `"5m"`, `"2.5m"`
- **Hours**: `"1h"`, `"0.5h"`
- **Plain numbers**: `30` (defaults to seconds)

### Regex Filtering Support
**NEW in v0.2.1**: Filter flog output with regular expressions to send only matching log events to OTLP endpoints.

Each step can include optional `filters` parameter with one or more regex patterns:

```yaml
steps:
  - start_time: "0s"
    interval: "30s"
    iterations: 5
    parameters:
      format: "apache_common"
      number: 1000
    filters:
      - "ERROR"                    # Match any line containing "ERROR"
      - "status.*[45][0-9][0-9]"  # Match 4xx/5xx HTTP status codes
      - "\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}" # Match IP addresses
```

**Filter Behavior**:
- **OR Logic**: Log events matching *any* filter pattern are sent to OTLP
- **No Filters**: All flog output is sent (default behavior)
- **Case Sensitive**: Use `(?i)pattern` for case-insensitive matching
- **Full Regex Support**: All Python regex features supported

**Common Filter Examples**:
```yaml
filters:
  - "(?i)error|warn|fail"           # Errors, warnings, failures
  - "POST.*api"                     # API POST requests
  - "user.{1,3}login"                   # User login events
  - "latency.{1,5}[5-9]\d{2,}ms"        # High latency (500ms+)
```

### Regex Replacement Support
**NEW in v0.2.1**: Transform flog output with regex-based substitutions using dynamic formatting variables.

Each step can include optional `replacements` parameter with pattern/replacement pairs:

```yaml
steps:
  - start_time: "0s"
    interval: "30s"
    iterations: 5
    parameters:
      format: "json"
      number: 100
    replacements:
      - pattern: "user_\\d+"
        replacement: "user_%n[1000,9999]"
      - pattern: "password=\\w+"
        replacement: "password=***"
      - pattern: "message=.*"
        replacement: "message=%s"
```

**Replacement Order**: Replacements are applied after filtering but before sending to OTLP.

**Formatting Variables**:
- `%s` - Lorem ipsum sentence using lorem-text
- `%n[x,y]` - Random integer between x and y (inclusive)
- `%e` - Current epoch timestamp  
- `%x[n]` - Lowercase hexadecimal with n characters (e.g., `%x[8]` → "a1b2c3d4")
- `%X[n]` - Uppercase hexadecimal with n characters (e.g., `%X[4]` → "A1B2")
- `%r[n]` - Random string of letters/digits with length n
- `%g` - GUID format (8-4-4-4-12 hex digits, e.g., "a1b2c3d4-e5f6-7890-abcd-ef0123456789")

**Common Replacement Examples**:
```yaml
replacements:
  # Anonymize user IDs with random numbers
  - pattern: "user_id=(\\d+)"
    replacement: "user_id=%n[10000,99999]"
  
  # Replace IP addresses with random IPs
  - pattern: "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}"
    replacement: "%n[1,255].%n[1,255].%n[1,255].%n[1,255]"
  
  # Generate session tokens
  - pattern: "session_token=\\w+"
    replacement: "session_token=%r[32]"
  
  # Add realistic error messages
  - pattern: "error_msg=null"
    replacement: "error_msg=%s"
  
  # Replace timestamps
  - pattern: "timestamp=\\d+"
    replacement: "timestamp=%e"
  
  # Generate transaction IDs  
  - pattern: "tx_id=\\w+"
    replacement: "tx_id=%X[8]"
  
  # Generate GUIDs for request tracking
  - pattern: "request_id=\\w+"
    replacement: "request_id=%g"
```

**Advanced Examples**:
```yaml
# Data masking and synthetic data generation
replacements:
  # Credit card numbers -> masked format
  - pattern: "card_number=\\d{16}"
    replacement: "card_number=****-****-****-%n[1000,9999]"
  
  # Email addresses -> anonymized  
  - pattern: "email=[\\w.-]+@[\\w.-]+\\.[a-zA-Z]{2,}"
    replacement: "email=user%n[1,999]@example.com"
  
  # Phone numbers -> random format
  - pattern: "phone=\\+?[\\d-()]+"  
    replacement: "phone=+1-%n[100,999]-%n[100,999]-%n[1000,9999]"
  
  # Generate realistic log messages with context
  - pattern: "message=\"[^\"]*\""
    replacement: "message=\"User action completed: %s Transaction ID: %r[8]\""
  
  # API correlation IDs with GUID format
  - pattern: "correlation_id=[\\w-]+"
    replacement: "correlation_id=%g"
  
  # Database record IDs
  - pattern: "record_id=\\d+"
    replacement: "record_id=%g"
```

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
You can create a compose file to include a local OTLP agent and receiver

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

```bash
# Build with uv (recommended - fastest and most reliable)
docker build -f Dockerfile.uv -t flog-otlp:uv .

# Standard build
docker build -t flog-otlp .

# Alternative build 
docker build -f Dockerfile.alt -t flog-otlp:alt .
```

## Recurring Executions Using --wait-time and --max-executions=1
This enables powerful use cases like continuous log generation for testing, scheduled batch processing, and long-running observability scenarios. These two parameters are applied in the wrapper rather than as parameters to flog, so will execute multiple flog commands in series. The wrapper can call your flog command and forward logs on a configurable interval.

### Smart Mode Detection
- **Single mode**: When wait-time=0 and max-executions=1 (default)
- **Recurring mode**: When wait-time>0 OR max-executions≠1

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

### Graceful Interruption

Ctrl+C stops gracefully with summary report so the current execution completes before stopping

### Detailed Logging
The wrapper provides detailed logging of execution, parameters and schedule activity and supports verbose mode.

```
2025-09-03 14:57:59 - otlp_log_sender - INFO - OTLP Log Sender for flog
2025-09-03 14:57:59 - otlp_log_sender - INFO - Configuration:
2025-09-03 14:57:59 - otlp_log_sender - INFO -   Endpoint: http://localhost:4318/v1/logs
2025-09-03 14:57:59 - otlp_log_sender - INFO -   Service Name: flog-generator
2025-09-03 14:57:59 - otlp_log_sender - INFO -   Send Delay: 0.1s
2025-09-03 14:57:59 - otlp_log_sender - INFO -   Log Format: apache_common
2025-09-03 14:57:59 - otlp_log_sender - INFO -   Log Count: 200
2025-09-03 14:57:59 - otlp_log_sender - INFO -   Duration: 10s
2025-09-03 14:57:59 - otlp_log_sender - INFO -   Wait Time: 0s
2025-09-03 14:57:59 - otlp_log_sender - INFO -   Max Executions: 1
2025-09-03 14:57:59 - otlp_log_sender - INFO -   Telemetry Attributes: {'app': 'web-server', 'debug': True}
2025-09-03 14:57:59 - otlp_log_sender - INFO - Using single execution mode
2025-09-03 14:57:59 - flog_otlp.sender.OTLPLogSender - INFO - Executing: flog -f apache_common -n 200 -s 10s
2025-09-03 14:57:59 - flog_otlp.sender.OTLPLogSender - INFO - Sending logs to: http://localhost:4318/v1/logs
^C2025-09-03 14:58:02 - flog_otlp.sender.OTLPLogSender - WARNING - Interrupted by user
2025-09-03 14:58:02 - otlp_log_sender - ERROR - Log processing completed with errors
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
