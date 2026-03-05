"""Scenario parsing and execution for flog-otlp."""

import logging
import random
import re
import string
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml
from lorem_text import lorem


class ScenarioStep:
    """Represents a single step in a scenario."""

    def __init__(self, step_data: Dict[str, Any], custom_strings: Dict[str, List[str]] = None):
        self.start_time_seconds = self._parse_duration(step_data.get("start_time", "0s"))
        self.interval_seconds = self._parse_duration(step_data.get("interval", "10s"))
        self.iterations = step_data.get("iterations", 1)
        self.parameters = step_data.get("parameters", {})
        self.filters = step_data.get("filters", [])
        self.replacements = step_data.get("replacements", [])
        self.custom_strings = custom_strings or {}

        # Compile regex patterns for efficiency
        self.compiled_filters = []
        if self.filters:
            import re

            for filter_pattern in self.filters:
                try:
                    self.compiled_filters.append(re.compile(filter_pattern))
                except re.error as e:
                    raise ValueError(f"Invalid regex filter pattern '{filter_pattern}': {e}") from e

        # Compile replacement patterns
        self.compiled_replacements = []
        if self.replacements:
            import re

            for replacement in self.replacements:
                if (
                    not isinstance(replacement, dict)
                    or "pattern" not in replacement
                    or "replacement" not in replacement
                ):
                    raise ValueError(
                        f"Invalid replacement format: {replacement}. Expected dict with 'pattern' and 'replacement' keys."
                    )
                try:
                    compiled_pattern = re.compile(replacement["pattern"])
                    self.compiled_replacements.append(
                        (compiled_pattern, replacement["replacement"])
                    )
                except re.error as e:
                    raise ValueError(
                        f"Invalid regex replacement pattern '{replacement['pattern']}': {e}"
                    ) from e

    def matches_filters(self, log_line: str) -> bool:
        """Check if a log line matches any of the regex filters."""
        if not self.compiled_filters:
            return True  # No filters means all logs pass through

        for pattern in self.compiled_filters:
            if pattern.search(log_line):
                return True
        return False

    def apply_replacements(self, log_line: str) -> str:
        """Apply regex replacements with formatting variables to a log line."""
        if not self.compiled_replacements:
            return log_line  # No replacements means return original line

        modified_line = log_line
        for pattern, replacement_template in self.compiled_replacements:
            # Apply formatting variables to replacement template
            formatted_replacement = self._format_replacement_variables(replacement_template)
            # Apply regex substitution using lambda to treat replacement as literal string
            modified_line = pattern.sub(lambda m: formatted_replacement, modified_line)

        return modified_line

    def _format_replacement_variables(self, template: str) -> str:
        """Format replacement variables in a template string."""
        result = template

        # %s - Lorem ipsum sentence
        if "%s" in result:
            sentence = lorem.sentence()
            result = result.replace("%s", sentence)

        # %n[x,y] - Random integer between x and y
        import re

        n_pattern = re.compile(r"%n\[(\d+),(\d+)\]")
        for match in n_pattern.finditer(template):
            min_val = int(match.group(1))
            max_val = int(match.group(2))
            random_int = str(random.randint(min_val, max_val))
            result = result.replace(match.group(0), random_int)

        # %e - Current epoch time
        if "%e" in result:
            epoch_time = str(int(time.time()))
            result = result.replace("%e", epoch_time)

        # %x[n] - Lowercase hexadecimal with length n
        hex_pattern = re.compile(r"%x\[(\d+)\]")
        for match in hex_pattern.finditer(template):
            length = int(match.group(1))
            max_value = (16**length) - 1
            format_str = f"0{length}x"
            hex_value = format(random.randint(0, max_value), format_str)
            result = result.replace(match.group(0), hex_value, 1)

        # %X[n] - Uppercase hexadecimal with length n
        hex_upper_pattern = re.compile(r"%X\[(\d+)\]")
        for match in hex_upper_pattern.finditer(template):
            length = int(match.group(1))
            max_value = (16**length) - 1
            format_str = f"0{length}X"
            hex_value = format(random.randint(0, max_value), format_str)
            result = result.replace(match.group(0), hex_value, 1)

        # %r[n] - Random string of letters and digits of length n
        r_pattern = re.compile(r"%r\[(\d+)\]")
        for match in r_pattern.finditer(template):
            length = int(match.group(1))
            chars = string.ascii_letters + string.digits
            random_string = "".join(random.choice(chars) for _ in range(length))
            result = result.replace(match.group(0), random_string, 1)

        # %g - GUID format (8-4-4-4-12 hexadecimal)
        if "%g" in result:
            # Generate 32 random hex digits
            hex_chars = "0123456789abcdef"
            guid_parts = [
                "".join(random.choice(hex_chars) for _ in range(8)),  # 8 digits
                "".join(random.choice(hex_chars) for _ in range(4)),  # 4 digits
                "".join(random.choice(hex_chars) for _ in range(4)),  # 4 digits
                "".join(random.choice(hex_chars) for _ in range(4)),  # 4 digits
                "".join(random.choice(hex_chars) for _ in range(12)),  # 12 digits
            ]
            guid = "-".join(guid_parts)
            result = result.replace("%g", guid)

        # %S[key] - Custom string from strings file
        s_pattern = re.compile(r"%S\[([^\]]+)\]")
        for match in s_pattern.finditer(template):
            key = match.group(1)
            if key in self.custom_strings:
                custom_string = random.choice(self.custom_strings[key])
                result = result.replace(match.group(0), custom_string, 1)
            else:
                # If key not found, replace with a placeholder indicating missing key
                result = result.replace(match.group(0), f"[MISSING_KEY:{key}]", 1)

        return result

    @staticmethod
    def _parse_duration(duration_str: str) -> float:
        """Parse duration string (e.g., '5m', '30s', '1h') to seconds."""
        if isinstance(duration_str, (int, float)):
            return float(duration_str)

        duration_str = str(duration_str).strip().lower()

        # Match patterns like "5m", "30s", "1h", "90"
        match = re.match(r"^(\d+(?:\.\d+)?)\s*([smh]?)$", duration_str)
        if not match:
            raise ValueError(f"Invalid duration format: {duration_str}")

        value, unit = match.groups()
        value = float(value)

        unit_multipliers = {
            "": 1,  # default to seconds if no unit
            "s": 1,  # seconds
            "m": 60,  # minutes
            "h": 3600,  # hours
        }

        if unit not in unit_multipliers:
            raise ValueError(f"Unsupported time unit: {unit}")

        return value * unit_multipliers[unit]


class ScenarioParser:
    """Parser for scenario YAML files."""

    def __init__(self, custom_strings: Dict[str, List[str]] = None):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.custom_strings = custom_strings or {}

    def load_scenario(self, scenario_path: str) -> Dict[str, Any]:
        """Load and parse a scenario YAML file."""
        scenario_data = self._load_yaml_file(scenario_path)
        self._validate_scenario_structure(scenario_data)
        steps = self._parse_scenario_steps(scenario_data["steps"])
        self._validate_step_timing(steps)

        return {
            "name": scenario_data["name"],
            "description": scenario_data.get("description", ""),
            "steps": steps,
        }

    def _load_yaml_file(self, scenario_path: str) -> Dict[str, Any]:
        """Load YAML file and return parsed data."""
        scenario_file = Path(scenario_path)

        if not scenario_file.exists():
            raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

        try:
            with open(scenario_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in scenario file: {e}") from e

    def _validate_scenario_structure(self, scenario_data: Any) -> None:
        """Validate the basic structure of scenario data."""
        if not isinstance(scenario_data, dict):
            raise ValueError("Scenario file must contain a YAML object")

        if "name" not in scenario_data:
            raise ValueError("Scenario must have a 'name' field")

        if "steps" not in scenario_data or not isinstance(scenario_data["steps"], list):
            raise ValueError("Scenario must have a 'steps' array")

        if not scenario_data["steps"]:
            raise ValueError("Scenario must have at least one step")

    def _parse_scenario_steps(self, steps_data: List[Dict[str, Any]]) -> List[ScenarioStep]:
        """Parse step data into ScenarioStep objects."""
        steps = []
        for i, step_data in enumerate(steps_data):
            try:
                step = ScenarioStep(step_data, self.custom_strings)
                steps.append(step)
            except Exception as e:
                raise ValueError(f"Error parsing step {i + 1}: {e}") from e
        return steps

    def _validate_step_timing(self, steps: List[ScenarioStep]) -> None:
        """Validate step timing is correct."""
        steps.sort(key=lambda s: s.start_time_seconds)
        for i, step in enumerate(steps):
            if step.start_time_seconds < 0:
                raise ValueError(
                    f"Step {i + 1} has negative start_time: {step.start_time_seconds}s"
                )

    def build_flog_command_from_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Build flog command from step parameters."""
        cmd = ["flog"]

        # Add format
        if "format" in parameters:
            cmd.extend(["-f", str(parameters["format"])])

        # Add number of logs
        if "number" in parameters:
            cmd.extend(["-n", str(parameters["number"])])

        # Add sleep duration
        if "sleep" in parameters:
            cmd.extend(["-s", str(parameters["sleep"])])

        # Add no-loop flag
        if parameters.get("no_loop"):
            cmd.append("--no-loop")

        # Add flog delay
        if "delay_flog" in parameters:
            cmd.extend(["-d", str(parameters["delay_flog"])])

        # Add rate limiting
        if "rate" in parameters:
            cmd.extend(["-r", str(parameters["rate"])])

        if "bytes" in parameters:
            cmd.extend(["-p", str(parameters["bytes"])])

        return cmd

    def get_total_scenario_duration(self, steps: List[ScenarioStep]) -> float:
        """Calculate total scenario duration in seconds."""
        if not steps:
            return 0

        max_end_time = 0
        for step in steps:
            # Calculate when the last iteration of this step will complete
            last_iteration_start = (
                step.start_time_seconds + (step.iterations - 1) * step.interval_seconds
            )
            # Estimate completion time (assume each iteration takes at least interval time)
            step_end_time = last_iteration_start + step.interval_seconds
            max_end_time = max(max_end_time, step_end_time)

        return max_end_time


class ScenarioExecutor:
    """Executes scenario steps with asynchronous timing control."""

    def __init__(self, otlp_sender, custom_strings: Dict[str, List[str]] = None):
        self.otlp_sender = otlp_sender
        self.custom_strings = custom_strings or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.scenario_start_time = None
        self.step_threads = []
        self.stop_event = threading.Event()

    def execute_scenario(self, scenario: Dict[str, Any], scenario_parser: ScenarioParser) -> bool:
        """Execute a complete scenario with asynchronous step execution."""
        scenario_name = scenario["name"]
        scenario_description = scenario["description"]
        steps = scenario["steps"]

        self.scenario_start_time = datetime.now(timezone.utc)
        self.logger.info(f"Starting scenario: {scenario_name}")
        if scenario_description:
            self.logger.info(f"Description: {scenario_description}")

        total_duration = scenario_parser.get_total_scenario_duration(steps)
        self.logger.info(f"Estimated total scenario duration: {total_duration:.1f}s")
        self.logger.info(f"Number of steps: {len(steps)}")

        # Schedule all steps asynchronously
        success = True
        try:
            for i, step in enumerate(steps, 1):
                self._schedule_step(i, step, scenario_parser)

            self.logger.info(f"All {len(steps)} steps scheduled. Waiting for completion...")

            # Wait for all steps to complete or user interrupt
            try:
                for thread in self.step_threads:
                    thread.join()
            except KeyboardInterrupt:
                self.logger.warning("Scenario interrupted by user")
                self.stop_event.set()
                success = False
                # Wait a bit for threads to stop gracefully
                for thread in self.step_threads:
                    thread.join(timeout=2)

        except Exception as e:
            self.logger.error(f"Scenario execution error: {e}")
            success = False

        end_time = datetime.now(timezone.utc)
        total_elapsed = (end_time - self.scenario_start_time).total_seconds()

        self.logger.info("SCENARIO COMPLETE")
        self.logger.info(f"Scenario: {scenario_name}")
        self.logger.info(f"Total time: {total_elapsed:.1f}s")
        self.logger.info(f"Started: {self.scenario_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self.logger.info(f"Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        return success

    def _schedule_step(self, step_number: int, step: ScenarioStep, scenario_parser: ScenarioParser):
        """Schedule a step for asynchronous execution."""

        def step_worker():
            try:
                # Wait for the step start time
                time_to_wait = step.start_time_seconds
                if time_to_wait > 0:
                    self.logger.info(
                        f"Step {step_number} scheduled to start in {time_to_wait:.1f}s"
                    )
                    time.sleep(time_to_wait)

                if self.stop_event.is_set():
                    return

                # Execute iterations of this step
                for iteration in range(step.iterations):
                    if self.stop_event.is_set():
                        break

                    if iteration > 0:
                        # Wait for the interval before next iteration
                        time.sleep(step.interval_seconds)

                    self._execute_step_iteration(step_number, iteration + 1, step, scenario_parser)

            except Exception as e:
                self.logger.error(f"Step {step_number} worker error: {e}")

        thread = threading.Thread(target=step_worker, name=f"Step-{step_number}")
        thread.daemon = True
        self.step_threads.append(thread)
        thread.start()

    def _execute_step_iteration(
        self, step_number: int, iteration: int, step: ScenarioStep, scenario_parser: ScenarioParser
    ):
        """Execute a single iteration of a scenario step."""
        iteration_start = datetime.now(timezone.utc)
        elapsed_since_start = (iteration_start - self.scenario_start_time).total_seconds()

        self.logger.info(
            f"Executing step {step_number}, iteration {iteration}/{step.iterations} at {iteration_start.strftime('%H:%M:%S UTC')} (T+{elapsed_since_start:.1f}s)"
        )

        # Build flog command from step parameters
        flog_cmd = scenario_parser.build_flog_command_from_parameters(step.parameters)

        # Log the flog command and parameters at info level
        self.logger.info(f"Step {step_number}.{iteration} flog command: {' '.join(flog_cmd)}")
        if step.parameters:
            self.logger.info(f"Step {step_number}.{iteration} parameters: {step.parameters}")
        if step.filters:
            self.logger.info(f"Step {step_number}.{iteration} regex filters: {step.filters}")

        # Create a temporary sender with step-specific parameters and filtering
        step_sender = self._create_step_sender(step.parameters)

        # Execute the step iteration with filtering
        success, log_count, filtered_count = self._process_flog_output_with_filters(
            step_sender, flog_cmd, step
        )

        iteration_end = datetime.now(timezone.utc)
        iteration_elapsed = (iteration_end - iteration_start).total_seconds()

        if success:
            if step.filters:
                self.logger.info(
                    f"Step {step_number}.{iteration} completed in {iteration_elapsed:.1f}s ({log_count} logs sent, {filtered_count} filtered out)"
                )
            else:
                self.logger.info(
                    f"Step {step_number}.{iteration} completed in {iteration_elapsed:.1f}s ({log_count} logs)"
                )
        else:
            self.logger.error(
                f"Step {step_number}.{iteration} failed after {iteration_elapsed:.1f}s"
            )

    def _process_flog_output_with_filters(self, sender, flog_cmd, step):
        """Execute flog and process output with optional regex filtering."""
        import subprocess

        self.logger.debug(f"Executing with filtering: {' '.join(flog_cmd)}")
        self.logger.debug(f"Sending logs to: {sender.endpoint}")

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
            sent_count = 0
            filtered_count = 0

            # Process each line of output with filtering
            for line in iter(process.stdout.readline, ""):
                if line.strip():  # Skip empty lines
                    line_count += 1

                    # Apply regex filters if present
                    if step.matches_filters(line.strip()):
                        # Log original line before any replacements (verbose mode)
                        self.logger.debug(f"Original log line before replacements: {line.strip()}")

                        # Apply replacements if present
                        processed_line = step.apply_replacements(line.strip())

                        # Detailed log line processing at DEBUG level
                        self.logger.debug(f"Processing line {sent_count + 1}: {processed_line}")

                        # Parse the processed log line
                        log_entry = sender.parse_flog_line(processed_line)

                        # Create OTLP payload
                        otlp_payload = sender.create_otlp_payload(log_entry)

                        # Send to endpoint
                        sender.send_log(otlp_payload)
                        sent_count += 1

                        # Configurable delay to avoid overwhelming the endpoint
                        if sender.delay > 0:
                            time.sleep(sender.delay)
                    else:
                        filtered_count += 1
                        self.logger.debug(
                            f"Filtered out line {line_count}: {line.strip()[:100]}..."
                        )

            # Wait for process to complete
            process.wait()

            if process.returncode != 0:
                stderr_output = process.stderr.read()
                self.logger.error(
                    f"flog process failed with return code {process.returncode}: {stderr_output}"
                )
                return False, sent_count, filtered_count

            self.logger.debug(
                f"Completed processing {line_count} total lines, {sent_count} sent, {filtered_count} filtered"
            )
            return True, sent_count, filtered_count

        except FileNotFoundError:
            self.logger.error("'flog' command not found. Please install flog first.")
            self.logger.error("Installation: go install github.com/mingrammer/flog@latest")
            return False, 0, 0
        except KeyboardInterrupt:
            self.logger.warning("Interrupted by user")
            if "process" in locals():
                process.terminate()
            return False, 0, 0
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False, 0, 0

    def _create_step_sender(self, parameters: Dict[str, Any]):
        """Create an OTLP sender with step-specific parameters."""
        from .parser import parse_key_value_pairs

        # Start with base sender configuration
        step_sender = type(self.otlp_sender)(
            endpoint=self.otlp_sender.endpoint,
            service_name=self.otlp_sender.service_name,
            delay=self.otlp_sender.delay,
            otlp_headers=self.otlp_sender.otlp_headers.copy(),
            otlp_attributes=self.otlp_sender.otlp_attributes.copy(),
            telemetry_attributes=self.otlp_sender.telemetry_attributes.copy(),
            log_format=parameters.get("format", self.otlp_sender.log_format),
        )

        # Override with step-specific attributes if provided
        if "otlp_attributes" in parameters:
            step_otlp_attributes = parse_key_value_pairs(parameters["otlp_attributes"])
            step_sender.otlp_attributes.update(step_otlp_attributes)

        if "telemetry_attributes" in parameters:
            step_telemetry_attributes = parse_key_value_pairs(parameters["telemetry_attributes"])
            step_sender.telemetry_attributes.update(step_telemetry_attributes)

        if "otlp_header" in parameters:
            step_headers = parse_key_value_pairs(parameters["otlp_header"])
            step_sender.otlp_headers.update(step_headers)

        # Override other step-specific parameters
        if "delay" in parameters:
            step_sender.delay = float(parameters["delay"])

        if "service_name" in parameters:
            step_sender.service_name = str(parameters["service_name"])

        if "otlp_endpoint" in parameters:
            step_sender.endpoint = str(parameters["otlp_endpoint"])

        return step_sender
