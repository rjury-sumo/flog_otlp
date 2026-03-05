"""OTLP and Sumo Logic log sender implementations."""

import json
import logging
import subprocess
import time
from datetime import datetime, timezone

import requests


class OTLPLogSender:
    def __init__(
        self,
        endpoint="http://localhost:4318/v1/logs",
        service_name="flog-generator",
        delay=0.1,
        otlp_headers=None,
        otlp_attributes=None,
        telemetry_attributes=None,
        log_format="apache_common",
    ):
        self.endpoint = endpoint
        self.service_name = service_name
        self.delay = delay
        self.log_format = log_format
        self.otlp_headers = otlp_headers or {}
        self.otlp_attributes = otlp_attributes or {}
        self.telemetry_attributes = telemetry_attributes or {}
        self.session = requests.Session()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Note: OTLP HTTP/JSON typically uses HTTP on port 4318
        # Use HTTPS (port 4318) only if your collector is specifically configured for it
        # For HTTPS, change endpoint to https://localhost:4318/v1/logs and uncomment below:

        # self.session.verify = False  # Only for self-signed certs
        # import urllib3
        # urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def parse_flog_line(self, line):
        """Parse a single flog line and extract relevant information"""
        try:
            # Try to parse as JSON first (if flog outputs JSON)
            log_data = json.loads(line)
            return {
                "message": log_data.get("message", line),
                "level": log_data.get("level", "INFO"),
                "timestamp": log_data.get(
                    "time", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                ),
            }
        except json.JSONDecodeError:
            # If not JSON, treat as plain text log
            return {
                "message": line.strip(),
                "level": "INFO",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }

    def create_otlp_payload(self, log_entry):
        """Create OTLP-compliant JSON payload"""
        # Convert timestamp to nanoseconds since Unix epoch (always in UTC)
        try:
            if log_entry["timestamp"].endswith("Z"):
                # ISO format with Z suffix (UTC)
                dt = datetime.fromisoformat(log_entry["timestamp"][:-1]).replace(
                    tzinfo=timezone.utc
                )
            else:
                # Try to parse as ISO format and assume UTC if no timezone info
                try:
                    dt = datetime.fromisoformat(log_entry["timestamp"])
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    # Fallback to current UTC time
                    dt = datetime.now(timezone.utc)
            timestamp_ns = int(dt.timestamp() * 1_000_000_000)
        except Exception:
            # Fallback to current UTC time
            timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)

        # Build resource attributes - start with defaults then add custom OTLP attributes
        resource_attributes = [
            {"key": "service.name", "value": {"stringValue": self.service_name}},
            {"key": "service.version", "value": {"stringValue": "1.0.0"}},
        ]

        # Add custom OTLP attributes to resource
        for key, value in self.otlp_attributes.items():
            resource_attributes.append({"key": key, "value": self._convert_attribute_value(value)})

        # Build log record attributes - start with defaults then add telemetry attributes
        log_attributes = [
            {"key": "log_source", "value": {"stringValue": "flog"}},
            {"key": "log_type", "value": {"stringValue": self.log_format}},
        ]

        # Add custom telemetry attributes to log record
        for key, value in self.telemetry_attributes.items():
            log_attributes.append({"key": key, "value": self._convert_attribute_value(value)})

        payload = {
            "resourceLogs": [
                {
                    "resource": {"attributes": resource_attributes},
                    "scopeLogs": [
                        {
                            "scope": {"name": "flog-processor", "version": "1.0.0"},
                            "logRecords": [
                                {
                                    "timeUnixNano": str(timestamp_ns),
                                    "severityText": log_entry["level"],
                                    "severityNumber": self.get_severity_number(log_entry["level"]),
                                    "body": {"stringValue": log_entry["message"]},
                                    "attributes": log_attributes,
                                    "traceId": "",
                                    "spanId": "",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        return payload

    def _convert_attribute_value(self, value):
        """Convert attribute value to OTLP format"""
        if isinstance(value, str):
            return {"stringValue": value}
        elif isinstance(value, bool):
            return {"boolValue": value}
        elif isinstance(value, int):
            return {"intValue": value}
        elif isinstance(value, float):
            return {"doubleValue": value}
        else:
            # Fallback to string representation
            return {"stringValue": str(value)}

    def get_severity_number(self, level):
        """Convert log level to OTLP severity number"""
        level_map = {
            "TRACE": 1,
            "DEBUG": 5,
            "INFO": 9,
            "WARN": 13,
            "WARNING": 13,
            "ERROR": 17,
            "FATAL": 21,
            "CRITICAL": 21,
        }
        return level_map.get(level.upper(), 9)  # Default to INFO

    def send_log(self, payload):
        """Send OTLP payload to the endpoint"""
        headers = {"Content-Type": "application/json", "User-Agent": "otlp-log-sender/1.0"}

        # Add custom OTLP headers
        headers.update(self.otlp_headers)

        try:
            response = self.session.post(self.endpoint, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                self.logger.debug("Log sent successfully")
            else:
                self.logger.error(f"Failed to send log: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")

    def process_flog_output(self, flog_cmd):
        """Execute flog and process its output"""
        self.logger.info(f"Executing: {' '.join(flog_cmd)}")
        self.logger.info(f"Sending logs to: {self.endpoint}")

        try:
            # Start flog process
            process = subprocess.Popen(
                flog_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            line_count = 0

            # Process each line of output
            for line in iter(process.stdout.readline, ""):
                if line.strip():  # Skip empty lines
                    line_count += 1
                    # Detailed log line processing at DEBUG level
                    self.logger.debug(f"Processing line {line_count}: {line.strip()[:100]}...")

                    # Parse the log line
                    log_entry = self.parse_flog_line(line)

                    # Create OTLP payload
                    otlp_payload = self.create_otlp_payload(log_entry)

                    # Send to endpoint
                    self.send_log(otlp_payload)

                    # Configurable delay to avoid overwhelming the endpoint
                    if self.delay > 0:
                        time.sleep(self.delay)

            # Wait for process to complete
            process.wait()

            if process.returncode != 0:
                stderr_output = process.stderr.read()
                self.logger.error(
                    f"flog process failed with return code {process.returncode}: {stderr_output}"
                )
                return False, line_count

            self.logger.info(f"Completed processing {line_count} log lines")
            return True, line_count

        except FileNotFoundError:
            self.logger.error("'flog' command not found. Please install flog first.")
            self.logger.error("Installation: go install github.com/mingrammer/flog@latest")
            return False, 0
        except KeyboardInterrupt:
            self.logger.warning("Interrupted by user")
            if "process" in locals():
                process.terminate()
            return False, 0
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False, 0

    def run_recurring_executions(self, flog_cmd, wait_time, max_executions):
        """Run flog executions on a recurring schedule"""
        execution_count = 0
        total_logs_processed = 0
        start_time = datetime.now(timezone.utc)

        self.logger.info("Starting recurring flog executions")
        self.logger.info(f"Wait time between executions: {wait_time}s")
        self.logger.info(
            f"Max executions: {'∞ (until stopped)' if max_executions == 0 else max_executions}"
        )
        self.logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        try:
            while max_executions == 0 or execution_count < max_executions:
                execution_count += 1
                execution_start = datetime.now(timezone.utc)

                self.logger.info(
                    f"Execution #{execution_count} started at {execution_start.strftime('%H:%M:%S UTC')}"
                )

                # Process flog output
                success, line_count = self.process_flog_output(flog_cmd)
                total_logs_processed += line_count

                execution_end = datetime.now(timezone.utc)
                execution_duration = (execution_end - execution_start).total_seconds()

                if success:
                    self.logger.info(
                        f"Execution #{execution_count} completed in {execution_duration:.1f}s ({line_count} logs)"
                    )
                else:
                    self.logger.warning(
                        f"Execution #{execution_count} failed after {execution_duration:.1f}s"
                    )

                # Check if we should continue
                if max_executions > 0 and execution_count >= max_executions:
                    break

                # Wait before next execution
                if wait_time > 0:
                    self.logger.info(f"Waiting {wait_time}s before next execution...")
                    time.sleep(wait_time)

        except KeyboardInterrupt:
            self.logger.warning(f"Stopped by user after {execution_count} executions")

        # Summary
        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - start_time).total_seconds()

        self.logger.info("EXECUTION SUMMARY:")
        self.logger.info(f"Total executions: {execution_count}")
        self.logger.info(f"Total logs processed: {total_logs_processed}")
        self.logger.info(f"Total runtime: {total_duration:.1f}s")
        self.logger.info(
            f"Average logs per execution: {total_logs_processed / execution_count if execution_count > 0 else 0:.1f}"
        )
        self.logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self.logger.info(f"Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        return execution_count > 0


class SumoLogicSender:
    """Sender for Sumo Logic HTTP Source endpoints."""

    def __init__(
        self,
        endpoint,
        delay=0.1,
        category=None,
        name=None,
        host=None,
        fields=None,
    ):
        self.endpoint = endpoint
        self.delay = delay
        self.category = category
        self.name = name
        self.host = host
        self.fields = fields or {}
        self.session = requests.Session()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _obfuscate_endpoint(self, endpoint):
        """Obfuscate the middle portion of the Sumo Logic endpoint URL for logging."""
        try:
            # Only obfuscate URLs that have /http/ or /https/ path (typical Sumo Logic pattern)
            if "/http/" not in endpoint and "/https/" not in endpoint:
                return endpoint

            # Find the last path segment (the token part after /http/)
            parts = endpoint.rsplit("/", 1)
            if len(parts) == 2:
                base_url, token = parts
                # Show first 5 and last 5 characters with *** in the middle
                if len(token) > 10:
                    obfuscated_token = f"{token[:5]}***{token[-5:]}"
                    return f"{base_url}/{obfuscated_token}"
            return endpoint
        except Exception:
            return endpoint

    def send_log(self, log_line):
        """Send a single log line to Sumo Logic HTTP source."""
        headers = {"Content-Type": "text/plain"}

        # Add optional Sumo Logic metadata headers
        if self.category:
            headers["X-Sumo-Category"] = self.category
        if self.name:
            headers["X-Sumo-Name"] = self.name
        if self.host:
            headers["X-Sumo-Host"] = self.host
        if self.fields:
            # Format fields as comma-separated key=value pairs
            fields_str = ",".join([f"{k}={v}" for k, v in self.fields.items()])
            headers["X-Sumo-Fields"] = fields_str

        try:
            response = self.session.post(
                self.endpoint, data=log_line.encode("utf-8"), headers=headers, timeout=10
            )

            if response.status_code == 200:
                self.logger.debug("Log sent successfully to Sumo Logic")
            else:
                self.logger.error(
                    f"Failed to send log to Sumo Logic: {response.status_code} - {response.text}"
                )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send log to Sumo Logic: {e}")

    def process_flog_output(self, flog_cmd):
        """Execute flog and process its output."""
        self.logger.info(f"Executing: {' '.join(flog_cmd)}")
        self.logger.info(f"Sending logs to Sumo Logic: {self._obfuscate_endpoint(self.endpoint)}")

        try:
            # Start flog process
            process = subprocess.Popen(
                flog_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            line_count = 0
            success_count = 0

            # Process each line of output
            for line in iter(process.stdout.readline, ""):
                if line.strip():  # Skip empty lines
                    line_count += 1
                    self.logger.debug(f"Processing line {line_count}: {line.strip()[:100]}...")

                    # Send raw log line to Sumo Logic
                    self.send_log(line.strip())
                    success_count += 1

                    # Configurable delay to avoid overwhelming the endpoint
                    if self.delay > 0:
                        time.sleep(self.delay)

            # Wait for process to complete
            process.wait()

            if process.returncode != 0:
                stderr_output = process.stderr.read()
                self.logger.error(
                    f"flog process failed with return code {process.returncode}: {stderr_output}"
                )
                return False, line_count

            self.logger.info(
                f"Completed processing {line_count} log lines ({success_count} sent successfully)"
            )
            return True, line_count

        except FileNotFoundError:
            self.logger.error("'flog' command not found. Please install flog first.")
            self.logger.error("Installation: go install github.com/mingrammer/flog@latest")
            return False, 0
        except KeyboardInterrupt:
            self.logger.warning("Interrupted by user")
            if "process" in locals():
                process.terminate()
            return False, 0
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False, 0

    def run_recurring_executions(self, flog_cmd, wait_time, max_executions):
        """Run flog executions on a recurring schedule."""
        execution_count = 0
        total_logs_processed = 0
        start_time = datetime.now(timezone.utc)

        self.logger.info("Starting recurring flog executions")
        self.logger.info(f"Wait time between executions: {wait_time}s")
        self.logger.info(
            f"Max executions: {'∞ (until stopped)' if max_executions == 0 else max_executions}"
        )
        self.logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        try:
            while max_executions == 0 or execution_count < max_executions:
                execution_count += 1
                execution_start = datetime.now(timezone.utc)

                self.logger.info(
                    f"Execution #{execution_count} started at {execution_start.strftime('%H:%M:%S UTC')}"
                )

                # Process flog output
                success, line_count = self.process_flog_output(flog_cmd)
                total_logs_processed += line_count

                execution_end = datetime.now(timezone.utc)
                execution_duration = (execution_end - execution_start).total_seconds()

                if success:
                    self.logger.info(
                        f"Execution #{execution_count} completed in {execution_duration:.1f}s ({line_count} logs)"
                    )
                else:
                    self.logger.warning(
                        f"Execution #{execution_count} failed after {execution_duration:.1f}s"
                    )

                # Check if we should continue
                if max_executions > 0 and execution_count >= max_executions:
                    break

                # Wait before next execution
                if wait_time > 0:
                    self.logger.info(f"Waiting {wait_time}s before next execution...")
                    time.sleep(wait_time)

        except KeyboardInterrupt:
            self.logger.warning(f"Stopped by user after {execution_count} executions")

        # Summary
        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - start_time).total_seconds()

        self.logger.info("EXECUTION SUMMARY:")
        self.logger.info(f"Total executions: {execution_count}")
        self.logger.info(f"Total logs processed: {total_logs_processed}")
        self.logger.info(f"Total runtime: {total_duration:.1f}s")
        self.logger.info(
            f"Average logs per execution: {total_logs_processed / execution_count if execution_count > 0 else 0:.1f}"
        )
        self.logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self.logger.info(f"Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        return execution_count > 0
