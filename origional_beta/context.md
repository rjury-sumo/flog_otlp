# Project Summary: flog-otlp Utility

## Overview
The **flog-otlp** utility is a Python-based log generation and forwarding tool that bridges the gap between synthetic log creation and OpenTelemetry Protocol (OTLP) observability pipelines. It combines the realistic log generation capabilities of [flog](https://github.com/mingrammer/flog) with OTLP-compliant log forwarding, making it an essential tool for testing, development, and validation of log processing systems.

## Architecture & Components

### Core Components
1. **OTLPLogSender Class**: Main orchestrator that handles flog execution, log parsing, OTLP payload creation, and HTTP transmission
2. **Argument Parser**: Comprehensive CLI interface supporting both flog parameters and OTLP-specific configuration
3. **Key-Value Parser**: Handles complex attribute and header parsing with type coercion
4. **Logging System**: Standard Python logging with configurable verbosity levels

### Data Flow
```
flog (subprocess) → stdout capture → log parsing → OTLP payload creation → HTTP POST → OTLP endpoint
```

### Key Dependencies
- **flog**: External Go-based log generator (subprocess execution)
- **requests**: HTTP client for OTLP endpoint communication
- **Standard library**: subprocess, json, datetime, argparse, logging

## Technical Specifications

### OTLP Compliance
- **Protocol**: OpenTelemetry Logs v1 over HTTP/JSON
- **Default Endpoint**: `http://localhost:4318/v1/logs`
- **Payload Structure**: Full OTLP resourceLogs format with resource attributes, scope metadata, and log records
- **Timestamp Handling**: UTC-normalized nanosecond timestamps
- **Attribute Types**: String, boolean, integer, and float values with automatic type detection

### Log Processing Pipeline
1. **Generation**: flog creates realistic log entries in various formats
2. **Parsing**: Line-by-line processing with JSON detection and fallback to plain text
3. **Transformation**: Convert to OTLP-compliant JSON structure
4. **Enrichment**: Add custom attributes at resource and log record levels
5. **Transmission**: HTTP POST with configurable headers and error handling

## Feature Categories

### Log Generation (flog Integration)
- **Formats**: apache_common, apache_combined, apache_error, rfc3164, rfc5424, common_log, json
- **Volume Control**: Configurable log count (-n) and time duration (-s)
- **Rate Limiting**: Logs per second (-r) and bytes per second (-p) controls
- **Behavior**: Loop control, delay settings, and output formatting

### OTLP Configuration
- **Endpoints**: Custom OTLP collector URLs with HTTP/HTTPS support
- **Authentication**: Custom headers for Bearer tokens, API keys, tenant IDs
- **Metadata**: Resource-level attributes (service info, environment, region)
- **Log Attributes**: Per-record attributes (application info, debug flags, user context)

### Execution Modes
- **Single Execution**: Generate and send logs once (default behavior)
- **Recurring Execution**: Scheduled repeated runs with configurable intervals
- **Continuous Operation**: Run indefinitely until manual termination (max-executions=0)

### Monitoring & Observability
- **Structured Logging**: Python logging with INFO/DEBUG/WARNING/ERROR levels
- **Execution Tracking**: Per-execution success/failure reporting
- **Performance Metrics**: Processing duration, log counts, throughput statistics
- **Summary Reports**: Comprehensive execution summaries with UTC timestamps

## Configuration Parameters

### Critical Parameters
- `--otlp-endpoint`: OTLP destination URL
- `--otlp-attributes`: Resource-level metadata (environment, region, service info)
- `--telemetry-attributes`: Log-level metadata (app info, user context, debug flags)
- `--otlp-header`: HTTP headers for authentication and routing
- `--wait-time`: Interval between recurring executions
- `--max-executions`: Total execution count (0 = infinite)

### flog Parameters (Passthrough)
- `-f/--format`: Log format selection
- `-n/--number`: Log entry count
- `-s/--sleep`: Generation duration
- `-r/--rate`: Rate limiting controls
- `--no-loop`: Disable flog's infinite mode

## Use Case Categories

### Testing & Validation
- **OTLP Collector Testing**: Verify log ingestion pipelines and processing rules
- **Schema Validation**: Test log parsing, field extraction, and data transformation
- **Performance Testing**: Load testing with controlled log volume and timing
- **Integration Testing**: End-to-end pipeline validation from generation to storage

### Development & Debugging
- **Local Development**: Generate test data for feature development
- **Pipeline Development**: Test log processing logic with realistic data
- **Configuration Testing**: Validate collector configurations and routing rules
- **Debug Workflows**: Reproduce issues with controlled log scenarios

### Operational Testing
- **Capacity Planning**: Determine system limits with synthetic load
- **Alerting Validation**: Trigger monitoring alerts with specific log patterns
- **Failover Testing**: Test collector redundancy and error handling
- **SLA Validation**: Verify processing performance meets requirements

## Technical Considerations

### Performance Characteristics
- **Memory Usage**: Line-by-line processing minimizes memory footprint
- **Network Efficiency**: Per-log HTTP requests with configurable delays
- **Error Resilience**: Graceful handling of network failures and collector downtime
- **Resource Control**: Configurable delays prevent endpoint overwhelming

### Security Features
- **Header Logging**: Sensitive authentication headers logged only at DEBUG level
- **SSL/TLS Support**: HTTPS endpoint support with certificate validation controls
- **Input Validation**: Malformed attribute handling with warning messages
- **Process Isolation**: flog executed as subprocess with proper cleanup

### Operational Considerations
- **Graceful Shutdown**: Ctrl+C handling with execution summaries
- **Error Recovery**: Continue processing on individual log send failures
- **Timezone Handling**: Consistent UTC timestamp normalization
- **Logging Verbosity**: Configurable detail level for debugging vs. production use

## Integration Patterns

### Common Deployment Scenarios
1. **CI/CD Pipelines**: Automated testing of log processing systems
2. **Development Environments**: Local testing with realistic log data
3. **Staging Validation**: Pre-production pipeline testing
4. **Load Testing**: Performance validation under controlled conditions
5. **Demo Systems**: Populate demonstrations with realistic log traffic

### Collector Integrations
- **OpenTelemetry Collector**: Primary target with HTTP receiver configuration
- **Jaeger**: Direct OTLP ingestion with trace correlation capabilities
- **Vendor Collectors**: Works with any OTLP-compliant log receiver
- **Proxy Patterns**: Can be used behind load balancers and API gateways

## Extension Points & Customization

### Attribute Customization
- **Resource Attributes**: Service metadata, deployment information, infrastructure tags
- **Log Attributes**: Application context, user information, request correlation
- **Dynamic Values**: Time-based, counter-based, or computed attribute values

### Header Customization
- **Authentication**: Bearer tokens, API keys, client certificates
- **Routing**: Tenant IDs, data classification, priority headers  
- **Metadata**: Client information, request tracking, feature flags

### Format Extensions
- **Custom flog Formats**: Support for any flog-compatible log format
- **Post-Processing**: Log content transformation before OTLP conversion
- **Payload Modification**: Custom OTLP payload structure adjustments

## Maintenance & Evolution

### Code Structure
- **Modular Design**: Separate concerns for parsing, OTLP creation, and transmission
- **Configuration Driven**: Extensive parameterization without code changes
- **Error Handling**: Comprehensive exception handling and recovery
- **Logging Integration**: Standard Python logging for operational visibility

### Future Enhancement Areas
- **Batch Processing**: Group multiple logs into single OTLP requests
- **Async Processing**: Non-blocking HTTP requests for higher throughput
- **Configuration Files**: YAML/JSON configuration file support
- **Metric Generation**: OTLP metrics alongside log generation
- **Trace Integration**: Correlated trace/log generation for complete observability testing

This utility serves as a bridge between synthetic log generation and modern observability infrastructure, enabling comprehensive testing and validation of OTLP-based log processing pipelines.