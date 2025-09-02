# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-09-02

### Added
- **Scenario Mode**: Execute complex log generation scenarios with YAML configuration files
  - Asynchronous step execution using threading for concurrent operations
  - Flexible scheduling with `start_time`, `interval`, and `iterations` parameters
  - Enhanced INFO-level logging showing flog commands and step parameters
  - Support for overlapping, parallel, and sequential execution patterns
- **Time Format Support**: Parse duration strings (`10s`, `5m`, `1h`) or plain numbers
- **Parameter Override**: Each scenario step can customize any flog-otlp parameter
- **Graceful Shutdown**: Proper thread cleanup on interruption (Ctrl+C)
- **Scenario Validation**: Comprehensive YAML structure and timing validation
- **Example Scenarios**: Included `example_scenario.yaml` with realistic test patterns

### Changed
- **CLI Interface**: Added `--scenario` parameter for YAML scenario file execution
- **Documentation**: Updated README.md with comprehensive scenario mode documentation
- **Architecture**: New `scenario.py` module with ScenarioParser and ScenarioExecutor classes
- **Dependencies**: Added PyYAML>=6.0.0 for YAML parsing support

### Technical Details
- **New Module**: `src/flog_otlp/scenario.py` - 275 lines of scenario processing logic
- **Test Coverage**: Added `tests/test_scenario.py` with 19 comprehensive test cases
- **Code Quality**: All tests passing (38/38), linting clean, type-safe implementation
- **Threading**: Daemon threads for concurrent step execution with proper synchronization
- **Logging**: Enhanced with step-by-step progress tracking and detailed parameter visibility

### Example Usage
```bash
# Execute a scenario from YAML file
flog-otlp --scenario scenario.yaml

# Combine with other options
flog-otlp --scenario load-test.yaml --otlp-endpoint https://collector:4318/v1/logs --verbose
```

### YAML Schema
```yaml
name: "My Test Scenario"
description: "Description of the test scenario"
steps:
  - start_time: "0s"     # When to start (relative to scenario start)
    interval: "30s"      # Time between iterations
    iterations: 5        # Number of times to run this step
    parameters:          # Any flog-otlp parameters
      format: "json"
      number: 100
      telemetry_attributes:
        - "service=web-app"
```

## [0.1.1] - 2025-08-27

### Changed
- Updated package metadata and documentation
- Improved installation instructions

## [0.1.0] - 2025-08-27

### Added
- Initial release with core OTLP log sending functionality
- Support for flog log generation and OTLP transmission
- Recurring execution modes with configurable timing
- Custom OTLP and telemetry attributes
- Docker support with multi-stage builds
- Comprehensive CLI with all flog parameters
- Full test suite and development tooling