# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2025-09-03

### Added
- **Custom Strings Support**: Load custom string arrays from YAML files for realistic log data generation
  - New `--strings-file` CLI parameter for specifying YAML file path containing string dictionaries
  - `%S[key]` formatting variable for random selection from custom string arrays
  - Comprehensive YAML validation ensuring proper structure (dictionary of string arrays)
  - Graceful error handling for missing keys with `[MISSING_KEY:keyname]` placeholders
  - Integration with scenario mode for domain-specific log generation
- **Example Strings File**: Comprehensive `example_strings.yaml` with 10+ categories including:
  - User names, service names, error messages, device types
  - Geographic locations, HTTP methods, log levels, business actions
  - Department names, transaction types, HTTP status codes
  - CEF (Common Event Format) sample logs for security scenarios
  - AWS account IDs for cloud logging scenarios

### Changed
- **CLI Interface**: Extended argument parsing to support strings file loading
- **Scenario Processing**: Updated ScenarioStep, ScenarioExecutor, and ScenarioParser to accept custom strings
- **Documentation**: Added comprehensive custom strings section to README.md with usage examples
- **Test Coverage**: Added 14 new test cases (8 for CLI strings + 6 for scenario integration)

### Technical Details
- **New Function**: `load_strings_file()` in `cli.py` with comprehensive YAML validation
- **Enhanced ScenarioStep**: Added custom_strings parameter and `%S[key]` token processing
- **Test Files**: 
  - `tests/test_cli_strings.py` - New test suite for strings file functionality
  - Extended `tests/test_scenario.py` with custom strings integration tests
- **Code Quality**: All 75 tests passing, clean linting, robust error handling
- **Architecture**: Seamless integration through CLI → ScenarioParser → ScenarioExecutor → ScenarioStep pipeline

### Example Usage
```bash
# Use custom strings file with scenario mode
flog-otlp --scenario scenario.yaml --strings-file example_strings.yaml

# Custom strings work with all other options
flog-otlp --scenario test.yaml --strings-file custom.yaml --otlp-endpoint https://collector:4318/v1/logs
```

### YAML Strings File Format
```yaml
users:
  - "alice.johnson"
  - "bob.smith"
  - "charlie.brown"

services:
  - "user-service"
  - "order-service" 
  - "payment-service"

error_messages:
  - "Connection timeout after 30 seconds"
  - "Invalid authentication credentials"
  - "Resource not found in database"
```

### Replacement Variable Usage
```yaml
# In scenario steps, use %S[key] to randomly select from string arrays
replacements:
  - pattern: "user=(\\w+)"
    replacement: "user=%S[users]"
  - pattern: "service=(\\w+)" 
    replacement: "service=%S[services]"
  - pattern: "error=(.*)"
    replacement: "error=%S[error_messages]"
```

## [0.2.1] - 2025-09-03

### Added
- **Regex Filtering**: Filter flog output with regular expressions to send only matching log events to OTLP endpoints
  - Optional `filters` parameter in scenario steps with OR logic for multiple patterns
  - Full Python regex support including case-insensitive matching with `(?i)` flag
  - Applied before replacements but after flog generation
  - Enhanced logging shows filtered vs sent counts
- **Regex Replacements**: Transform flog output with regex-based substitutions using dynamic formatting variables
  - Optional `replacements` parameter with pattern/replacement pairs
  - Applied after filtering but before sending to OTLP endpoints
  - Support for data anonymization and synthetic data generation
- **Formatting Variables**: Dynamic content generation for realistic log data
  - `%s` - Lorem ipsum sentences using lorem-text library
  - `%n[x,y]` - Random integers between x and y (inclusive)
  - `%e` - Current epoch timestamp
  - `%x[n]` - Configurable lowercase hexadecimal with n characters
  - `%X[n]` - Configurable uppercase hexadecimal with n characters
  - `%r[n]` - Random alphanumeric strings with length n
  - `%g` - GUID format (8-4-4-4-12 hex digits with hyphens)

### Changed
- **Dependencies**: Added `lorem-text>=2.1.0` for realistic sentence generation
- **YAML Schema**: Extended scenario steps to support `filters` and `replacements` arrays
- **Processing Pipeline**: Log processing now follows: flog → filtering → replacement → OTLP transmission
- **Example Scenario**: Updated with comprehensive filtering and replacement examples

### Technical Details
- **Enhanced ScenarioStep Class**: Added regex compilation for filters and replacements with proper error handling
- **New Methods**: 
  - `matches_filters()` - Apply OR logic regex filtering
  - `apply_replacements()` - Transform log content with formatting variables
  - `_format_replacement_variables()` - Process dynamic formatting tokens
- **Test Coverage**: Added 15 new test cases covering filtering and replacement functionality
- **Code Quality**: All 61 tests passing, clean linting, comprehensive error handling

### Example Usage
```yaml
name: "Advanced Log Processing"
steps:
  - start_time: "0s"
    interval: "30s"
    iterations: 10
    parameters:
      format: "json"
      number: 100
    filters:
      - "ERROR|WARN"              # Match error/warning logs
      - "[45][0-9][0-9]"         # Match 4xx/5xx HTTP codes
    replacements:
      - pattern: "user_id=\\d+"
        replacement: "user_id=%n[10000,99999]"
      - pattern: "session_token=\\w+"
        replacement: "session_token=%x[32]"
      - pattern: "request_id=\\w+"
        replacement: "request_id=%g"
```

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