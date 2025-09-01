"""Command-line interface for flog-otlp."""

import argparse
import sys

from .logging_config import setup_logging
from .parser import parse_key_value_pairs
from .sender import OTLPLogSender


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="OTLP Log Sender for flog - Generate logs and send to OTLP endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Default: 200 logs over 10 seconds (single execution)
  %(prog)s -n 100 -s 5s                 # 100 logs over 5 seconds (single execution)
  %(prog)s -f apache_common -n 50       # 50 Apache common format logs (single execution)
  %(prog)s -f json -n 100 --no-loop     # 100 JSON logs, no infinite loop (single execution)
  %(prog)s --otlp-endpoint https://collector:4318/v1/logs  # Custom endpoint (single execution)

  # Recurring executions:
  %(prog)s --wait-time 30 --max-executions 10    # Run 10 times, 30s between executions
  %(prog)s --wait-time 60 --max-executions 0     # Run forever, 60s between executions
  %(prog)s -n 50 -s 5s --wait-time 10 --max-executions 5  # 5 executions: 50 logs/5s, 10s wait

  # Custom attributes and headers:
  %(prog)s --otlp-attributes environment=production --otlp-attributes region=us-east-1
  %(prog)s --telemetry-attributes app=web-server --telemetry-attributes debug=true
  %(prog)s --otlp-header "Authorization=Bearer token123" --otlp-header "X-Custom=value"

Supported log formats:
  apache_common, apache_combined, apache_error, rfc3164, rfc5424, common_log, json
        """,
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
        default="10s",
        help="Duration to generate logs over (e.g., 10s, 2m, 1h) (default: 10s)",
    )

    # flog options - behavior
    parser.add_argument("--no-loop", action="store_true", help="Disable infinite loop mode")

    parser.add_argument("-d", "--delay-flog", help="Delay between log generation (flog -d option)")

    # flog options - rate limiting
    parser.add_argument("-r", "--rate", type=int, help="Rate limit in logs per second")

    parser.add_argument("-p", "--bytes", type=int, help="Bytes limit per second")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

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

    # Parse custom attributes and headers
    otlp_attributes = parse_key_value_pairs(args.otlp_attributes)
    telemetry_attributes = parse_key_value_pairs(args.telemetry_attributes)
    otlp_headers = parse_key_value_pairs(args.otlp_header)

    # Log configuration details
    logger.info("Configuration:")
    logger.info(f"  Endpoint: {args.otlp_endpoint}")
    logger.info(f"  Service Name: {args.service_name}")
    logger.info(f"  Send Delay: {args.delay}s")
    logger.info(f"  Log Format: {args.format}")
    logger.info(f"  Log Count: {args.number}")
    logger.info(f"  Duration: {args.sleep}")
    logger.info(f"  Wait Time: {args.wait_time}s")
    logger.info(f"  Max Executions: {'∞' if args.max_executions == 0 else args.max_executions}")

    if otlp_attributes:
        logger.info(f"  OTLP Attributes: {otlp_attributes}")
    if telemetry_attributes:
        logger.info(f"  Telemetry Attributes: {telemetry_attributes}")
    if otlp_headers:
        logger.debug(f"  Custom Headers: {otlp_headers}")  # Headers may contain sensitive data

    # Build flog command
    flog_cmd = build_flog_command(args)
    logger.debug(f"Built flog command: {' '.join(flog_cmd)}")

    # Create sender instance with custom parameters
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
