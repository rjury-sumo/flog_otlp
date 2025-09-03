"""Tests for scenario functionality."""

import tempfile
from unittest.mock import Mock

import pytest
import yaml

from flog_otlp.scenario import ScenarioExecutor, ScenarioParser, ScenarioStep


class TestScenarioStep:
    """Tests for ScenarioStep class."""

    def test_parse_duration_seconds(self):
        """Test parsing duration in seconds."""
        step = ScenarioStep({"start_time": "30s", "interval": "60s", "iterations": 2})
        assert step.start_time_seconds == 30.0
        assert step.interval_seconds == 60.0
        assert step.iterations == 2

    def test_parse_duration_minutes(self):
        """Test parsing duration in minutes."""
        step = ScenarioStep({"start_time": "5m", "interval": "2m", "iterations": 3})
        assert step.start_time_seconds == 300.0
        assert step.interval_seconds == 120.0
        assert step.iterations == 3

    def test_parse_duration_hours(self):
        """Test parsing duration in hours."""
        step = ScenarioStep({"start_time": "1h", "interval": "0.5h", "iterations": 1})
        assert step.start_time_seconds == 3600.0
        assert step.interval_seconds == 1800.0
        assert step.iterations == 1

    def test_parse_numeric_values(self):
        """Test parsing numeric values (defaults to seconds)."""
        step = ScenarioStep({"start_time": 45, "interval": 90.5, "iterations": 4})
        assert step.start_time_seconds == 45.0
        assert step.interval_seconds == 90.5
        assert step.iterations == 4

    def test_parse_duration_invalid_format(self):
        """Test parsing invalid duration format."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            ScenarioStep({"start_time": "invalid", "interval": "10s"})

    def test_parse_duration_invalid_unit(self):
        """Test parsing invalid time unit."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            ScenarioStep({"start_time": "10x", "interval": "10s"})

    def test_default_values(self):
        """Test default values for step parameters."""
        step = ScenarioStep({})
        assert step.start_time_seconds == 0.0
        assert step.interval_seconds == 10.0
        assert step.iterations == 1
        assert step.parameters == {}

    def test_parameters_stored(self):
        """Test that parameters are stored correctly."""
        params = {"format": "json", "number": 100}
        step = ScenarioStep({"parameters": params})
        assert step.parameters == params

    def test_filters_stored(self):
        """Test that regex filters are stored and compiled correctly."""
        filters = [r"ERROR", r"WARN.*database"]
        step = ScenarioStep({"filters": filters})
        assert step.filters == filters
        assert len(step.compiled_filters) == 2

    def test_invalid_regex_filter(self):
        """Test error handling for invalid regex patterns."""
        with pytest.raises(ValueError, match="Invalid regex filter pattern"):
            ScenarioStep({"filters": [r"[unclosed"]})

    def test_matches_filters_no_filters(self):
        """Test that logs pass through when no filters are defined."""
        step = ScenarioStep({})
        assert step.matches_filters("any log line") is True

    def test_matches_filters_with_match(self):
        """Test that matching logs pass through filters."""
        step = ScenarioStep({"filters": [r"ERROR", r"status.*500"]})
        assert step.matches_filters("ERROR: Connection failed") is True
        assert step.matches_filters("status code 500") is True
        assert step.matches_filters("INFO: All good") is False

    def test_matches_filters_multiple_patterns(self):
        """Test OR logic with multiple regex patterns."""
        step = ScenarioStep({"filters": [r"user.*login", r"POST.*api", r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"]})

        # Should match user login pattern
        assert step.matches_filters("user john login successful") is True

        # Should match POST API pattern
        assert step.matches_filters("POST /api/users") is True

        # Should match IP address pattern
        assert step.matches_filters("Request from 192.168.1.1") is True

        # Should not match any pattern
        assert step.matches_filters("GET /static/image.png") is False

    def test_matches_filters_case_sensitive(self):
        """Test that regex matching is case-sensitive by default."""
        step = ScenarioStep({"filters": [r"Error"]})
        assert step.matches_filters("Error occurred") is True
        assert step.matches_filters("error occurred") is False

    def test_matches_filters_case_insensitive(self):
        """Test case-insensitive regex patterns."""
        step = ScenarioStep({"filters": [r"(?i)error"]})
        assert step.matches_filters("Error occurred") is True
        assert step.matches_filters("error occurred") is True
        assert step.matches_filters("ERROR occurred") is True


class TestScenarioParser:
    """Tests for ScenarioParser class."""

    def test_load_scenario_success(self):
        """Test successful scenario loading."""
        scenario_data = {
            "name": "Test Scenario",
            "description": "Test description",
            "steps": [
                {
                    "start_time": "0s",
                    "interval": "30s",
                    "iterations": 2,
                    "parameters": {"format": "json", "number": 50}
                },
                {
                    "start_time": "60s",
                    "interval": "45s",
                    "iterations": 3,
                    "parameters": {"format": "apache_common", "number": 100}
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(scenario_data, f)
            f.flush()

            parser = ScenarioParser()
            scenario = parser.load_scenario(f.name)

            assert scenario['name'] == "Test Scenario"
            assert scenario['description'] == "Test description"
            assert len(scenario['steps']) == 2
            assert scenario['steps'][0].start_time_seconds == 0.0
            assert scenario['steps'][0].iterations == 2
            assert scenario['steps'][1].start_time_seconds == 60.0
            assert scenario['steps'][1].iterations == 3

    def test_load_scenario_file_not_found(self):
        """Test error when scenario file doesn't exist."""
        parser = ScenarioParser()
        with pytest.raises(FileNotFoundError, match="Scenario file not found"):
            parser.load_scenario("nonexistent.yaml")

    def test_load_scenario_invalid_yaml(self):
        """Test error when YAML is invalid."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content:\n  - bad indentation")
            f.flush()

            parser = ScenarioParser()
            with pytest.raises(ValueError, match="Invalid YAML"):
                parser.load_scenario(f.name)

    def test_load_scenario_missing_name(self):
        """Test error when scenario is missing name."""
        scenario_data = {"steps": [{"start_time": "0s"}]}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(scenario_data, f)
            f.flush()

            parser = ScenarioParser()
            with pytest.raises(ValueError, match="Scenario must have a 'name' field"):
                parser.load_scenario(f.name)

    def test_load_scenario_missing_steps(self):
        """Test error when scenario is missing steps."""
        scenario_data = {"name": "Test"}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(scenario_data, f)
            f.flush()

            parser = ScenarioParser()
            with pytest.raises(ValueError, match="Scenario must have a 'steps' array"):
                parser.load_scenario(f.name)

    def test_load_scenario_empty_steps(self):
        """Test error when steps array is empty."""
        scenario_data = {"name": "Test", "steps": []}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(scenario_data, f)
            f.flush()

            parser = ScenarioParser()
            with pytest.raises(ValueError, match="Scenario must have at least one step"):
                parser.load_scenario(f.name)

    def test_build_flog_command_from_parameters(self):
        """Test building flog command from parameters."""
        parser = ScenarioParser()
        params = {
            "format": "json",
            "number": 100,
            "sleep": "30s",
            "no_loop": True,
            "delay_flog": "0.5s",
            "rate": 10,
            "bytes": 1024
        }

        cmd = parser.build_flog_command_from_parameters(params)
        expected = ["flog", "-f", "json", "-n", "100", "-s", "30s", "--no-loop", "-d", "0.5s", "-r", "10", "-p", "1024"]
        assert cmd == expected

    def test_build_flog_command_minimal_parameters(self):
        """Test building flog command with minimal parameters."""
        parser = ScenarioParser()
        cmd = parser.build_flog_command_from_parameters({})
        assert cmd == ["flog"]

    def test_get_total_scenario_duration(self):
        """Test calculating total scenario duration."""
        steps = [
            ScenarioStep({"start_time": "0s", "interval": "30s", "iterations": 2}),
            ScenarioStep({"start_time": "30s", "interval": "60s", "iterations": 1}),
            ScenarioStep({"start_time": "60s", "interval": "30s", "iterations": 3})
        ]

        parser = ScenarioParser()
        total_duration = parser.get_total_scenario_duration(steps)
        # Step 1: last iteration at 0+1*30=30, ends at 30+30=60
        # Step 2: last iteration at 30+0*60=30, ends at 30+60=90
        # Step 3: last iteration at 60+2*30=120, ends at 120+30=150
        assert total_duration == 150.0

    def test_get_total_scenario_duration_empty(self):
        """Test calculating duration for empty steps."""
        parser = ScenarioParser()
        assert parser.get_total_scenario_duration([]) == 0


class TestScenarioExecutor:
    """Tests for ScenarioExecutor class."""

    def test_executor_initialization(self):
        """Test that executor initializes properly."""
        mock_sender = Mock()
        executor = ScenarioExecutor(mock_sender)
        assert executor.otlp_sender == mock_sender
        assert executor.logger is not None

