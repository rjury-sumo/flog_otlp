"""Command-line interface for flog-otlp."""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

import yaml

from .logging_config import setup_logging
from .parser import parse_key_value_pairs
from .scenario import ScenarioExecutor, ScenarioParser
from .sender import OTLPLogSender, SumoLogicSender


def load_strings_file(strings_file_path: str) -> Dict[str, List[str]]:
    """Load and validate strings file containing custom string arrays."""
    strings_file = Path(strings_file_path)

    if not strings_file.exists():
        raise FileNotFoundError(f"Strings file not found: {strings_file_path}")

    try:
        with open(strings_file, "r", encoding="utf-8") as f:
            strings_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in strings file: {e}") from e

    if not isinstance(strings_data, dict):
        raise ValueError("Strings file must contain a YAML object with string arrays")

    # Validate that all values are lists of strings
    validated_strings = {}
    for key, value in strings_data.items():
        if not isinstance(value, list):
            raise ValueError(f"Key '{key}' must be a list of strings, got {type(value).__name__}")

        string_list = []
        for i, item in enumerate(value):
            if not isinstance(item, str):
                raise ValueError(
                    f"Key '{key}', item {i}: expected string, got {type(item).__name__}"
                )
            string_list.append(item)

        if not string_list:
            raise ValueError(f"Key '{key}' must contain at least one string")

        validated_strings[key] = string_list

    return validated_strings


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="OTLP Log Sender for flog - Generate logs and send to OTLP endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Default: 200 logs (single execution)
  %(prog)s -n 100 -s 5s                 # 100 logs over 5 seconds (single execution)
  %(prog)s -f apache_common -n 50       # 50 Apache common format logs (single execution)
  %(prog)s -f json -n 100 --no-loop     # 100 JSON logs, no infinite loop (single execution)
  %(prog)s --otlp-endpoint https://collector:4318/v1/logs  # Custom endpoint (single execution)

  # Recurring executions:
  %(prog)s --wait-time 30 --max-executions 10    # Run 10 times, 30s between executions
  %(prog)s --wait-time 60 --max-executions 0     # Run forever, 60s between executions
  %(prog)s -n 50 -s 5s --wait-time 10 --max-executions 5  # 5 executions: 50 logs/5s, 10s wait

  # Scenario executions:
  %(prog)s --scenario scenario.yaml              # Execute scenario from YAML file

  # Sumo Logic HTTP Source:
  %(prog)s --output-type sumologic --sumo-endpoint "https://endpoint.sumologic.com/..." -n 100 -f json
  %(prog)s --output-type sumologic --sumo-endpoint "https://..." --sumo-category "app/logs" --sumo-fields "env=prod"

  # Custom attributes and headers (OTLP):
  %(prog)s --otlp-attributes environment=production --otlp-attributes region=us-east-1
  %(prog)s --telemetry-attributes app=web-server --telemetry-attributes debug=true
  %(prog)s --otlp-header "Authorization=Bearer token123" --otlp-header "X-Custom=value"

Supported log formats:
  apache_common, apache_combined, apache_error, rfc3164, rfc5424, common_log, json
        """,
    )

    # Output type selection
    parser.add_argument(
        "--output-type",
        choices=["otlp", "sumologic"],
        default="otlp",
        help="Output destination type: otlp or sumologic (default: otlp)",
    )

    # OTLP-specific options (matching telemetrygen)
    parser.add_argument(
        "--otlp-endpoint",
        default="http://localhost:4318/v1/logs",
        help="Destination endpoint for exporting logs (default: http://localhost:4318/v1/logs)",
    )

    parser.add_argument(
        "--otlp-attributes",
        action="append",
        help="Custom OTLP resource attributes. Format: key=value, key=true, key=false, or key=123. Can be repeated.",
    )

    parser.add_argument(
        "--otlp-header",
        action="append",
        help="Custom header for OTLP requests. Format: key=value. Can be repeated.",
    )

    parser.add_argument(
        "--telemetry-attributes",
        action="append",
        help="Custom telemetry log attributes. Format: key=value, key=true, key=false, or key=123. Can be repeated.",
    )

    parser.add_argument(
        "--service-name",
        default="flog-generator",
        help="Service name for OTLP resource attributes (default: flog-generator)",
    )

    parser.add_argument(
        "--delay", type=float, default=0.1, help="Delay between log sends in seconds (default: 0.1)"
    )

    # Sumo Logic specific options
    parser.add_argument(
        "--sumo-endpoint",
        help="Sumo Logic HTTP source endpoint URL (required when --output-type=sumologic)",
    )

    parser.add_argument(
        "--sumo-category",
        help="Custom source category for Sumo Logic (X-Sumo-Category header)",
    )

    parser.add_argument(
        "--sumo-name",
        help="Custom source name for Sumo Logic (X-Sumo-Name header)",
    )

    parser.add_argument(
        "--sumo-host",
        help="Custom source host for Sumo Logic (X-Sumo-Host header)",
    )

    parser.add_argument(
        "--sumo-fields",
        action="append",
        help="Custom fields for Sumo Logic. Format: key=value. Can be repeated. (X-Sumo-Fields header)",
    )

    # Recurring execution options
    parser.add_argument(
        "--wait-time",
        type=float,
        default=0,
        help="Wait time in seconds between flog executions (default: 0 - single execution)",
    )

    parser.add_argument(
        "--max-executions",
        type=int,
        default=1,
        help="Number of flog executions (0 = run until manually stopped, default: 1)",
    )

    # flog options - main parameters
    parser.add_argument(
        "-f",
        "--format",
        choices=[
            "apache_common",
            "apache_combined",
            "apache_error",
            "rfc3164",
            "rfc5424",
            "common_log",
            "json",
        ],
        default="apache_common",
        help="Log format (default: apache_common)",
    )

    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=200,
        help="Number of log lines to generate (default: 200)",
    )

    parser.add_argument(
        "-s",
        "--sleep",
        default=None,
        help="Duration to generate logs over (e.g., 10s, 2m, 1h)",
    )

    # flog options - behavior
    parser.add_argument("--no-loop", action="store_true", help="Disable infinite loop mode")

    parser.add_argument("-d", "--delay-flog", help="Delay between log generation (flog -d option)")

    # flog options - rate limiting
    parser.add_argument("-r", "--rate", type=int, help="Rate limit in logs per second")

    parser.add_argument("-p", "--bytes", type=int, help="Bytes limit per second")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    # Scenario mode
    parser.add_argument(
        "--scenario",
        help="Path to YAML scenario file. When specified, executes the scenario instead of single/recurring mode.",
    )

    parser.add_argument(
        "--strings-file",
        help="Path to YAML file containing custom string arrays for %%S[key] replacement tokens.",
    )

    return parser.parse_args()


def build_flog_command(args):
    """Build flog command from parsed arguments"""
    cmd = ["flog"]

    # Add format
    if args.format:
        cmd.extend(["-f", args.format])

    # Add number of logs
    if args.number:
        cmd.extend(["-n", str(args.number)])

    # Add sleep duration
    if args.sleep:
        cmd.extend(["-s", args.sleep])

    # Add no-loop flag
    if args.no_loop:
        cmd.append("--no-loop")

    # Add flog delay
    if args.delay_flog:
        cmd.extend(["-d", args.delay_flog])

    # Add rate limiting
    if args.rate:
        cmd.extend(["-r", str(args.rate)])

    if args.bytes:
        cmd.extend(["-p", str(args.bytes)])

    return cmd


def main():
    # Parse command line arguments
    args = parse_args()

    # Setup logging based on verbose flag
    logger = setup_logging(verbose=args.verbose)

    logger.info("OTLP Log Sender for flog")

    # Validate output-type specific requirements
    if args.output_type == "sumologic":
        if not args.sumo_endpoint:
            logger.error("--sumo-endpoint is required when --output-type=sumologic")
            sys.exit(1)

    # Create sender instance based on output type
    if args.output_type == "sumologic":
        # Parse Sumo Logic fields
        sumo_fields = parse_key_value_pairs(args.sumo_fields)

        sender = SumoLogicSender(
            endpoint=args.sumo_endpoint,
            delay=args.delay,
            category=args.sumo_category,
            name=args.sumo_name,
            host=args.sumo_host,
            fields=sumo_fields,
        )
    else:  # otlp
        # Parse custom attributes and headers
        otlp_attributes = parse_key_value_pairs(args.otlp_attributes)
        telemetry_attributes = parse_key_value_pairs(args.telemetry_attributes)
        otlp_headers = parse_key_value_pairs(args.otlp_header)

        sender = OTLPLogSender(
            endpoint=args.otlp_endpoint,
            service_name=args.service_name,
            delay=args.delay,
            otlp_headers=otlp_headers,
            otlp_attributes=otlp_attributes,
            telemetry_attributes=telemetry_attributes,
            log_format=args.format,
        )

    # Determine execution mode
    if args.scenario:
        # Scenario execution mode
        logger.info("Using scenario execution mode")
        logger.info(f"Scenario file: {args.scenario}")

        # Load custom strings if provided
        custom_strings = {}
        if args.strings_file:
            logger.info(f"Loading custom strings from: {args.strings_file}")
            try:
                custom_strings = load_strings_file(args.strings_file)
                logger.info(f"Loaded custom strings with keys: {list(custom_strings.keys())}")
            except Exception as e:
                logger.error(f"Failed to load strings file: {e}")
                sys.exit(1)

        try:
            scenario_parser = ScenarioParser(custom_strings)
            scenario = scenario_parser.load_scenario(args.scenario)

            executor = ScenarioExecutor(sender, custom_strings)
            success = executor.execute_scenario(scenario, scenario_parser)
        except Exception as e:
            logger.error(f"Scenario execution failed: {e}")
            sys.exit(1)
    else:
        # Log configuration details for non-scenario modes
        logger.info("Configuration:")
        logger.info(f"  Output Type: {args.output_type}")

        if args.output_type == "sumologic":
            logger.info(f"  Endpoint: {sender._obfuscate_endpoint(args.sumo_endpoint)}")
            if args.sumo_category:
                logger.info(f"  Category: {args.sumo_category}")
            if args.sumo_name:
                logger.info(f"  Name: {args.sumo_name}")
            if args.sumo_host:
                logger.info(f"  Host: {args.sumo_host}")
            if sender.fields:
                logger.info(f"  Fields: {sender.fields}")
        else:  # otlp
            logger.info(f"  Endpoint: {args.otlp_endpoint}")
            logger.info(f"  Service Name: {args.service_name}")
            if otlp_attributes:
                logger.info(f"  OTLP Attributes: {otlp_attributes}")
            if telemetry_attributes:
                logger.info(f"  Telemetry Attributes: {telemetry_attributes}")
            if otlp_headers:
                logger.debug(
                    f"  Custom Headers: {otlp_headers}"
                )  # Headers may contain sensitive data

        logger.info(f"  Send Delay: {args.delay}s")
        logger.info(f"  Log Format: {args.format}")
        logger.info(f"  Log Count: {args.number}")
        logger.info(f"  Duration: {args.sleep}")
        logger.info(f"  Wait Time: {args.wait_time}s")
        logger.info(f"  Max Executions: {'∞' if args.max_executions == 0 else args.max_executions}")

        # Build flog command
        flog_cmd = build_flog_command(args)
        logger.debug(f"Built flog command: {' '.join(flog_cmd)}")

        if args.wait_time > 0 or args.max_executions != 1:
            # Recurring execution mode
            logger.info("Using recurring execution mode")
            success = sender.run_recurring_executions(flog_cmd, args.wait_time, args.max_executions)
        else:
            # Single execution mode
            logger.info("Using single execution mode")
            success, _ = sender.process_flog_output(flog_cmd)

    if success:
        logger.info("All logs processed successfully")
    else:
        logger.error("Log processing completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
