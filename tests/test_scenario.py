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
        step = ScenarioStep(
            {"filters": [r"user.*login", r"POST.*api", r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"]}
        )

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

    def test_replacements_stored_and_compiled(self):
        """Test that replacements are stored and compiled correctly."""
        replacements = [
            {"pattern": r"user_(\d+)", "replacement": "user_%n[1000,9999]"},
            {"pattern": r"timestamp:\d+", "replacement": "timestamp:%e"},
        ]
        step = ScenarioStep({"replacements": replacements})
        assert step.replacements == replacements
        assert len(step.compiled_replacements) == 2

    def test_invalid_replacement_format(self):
        """Test error handling for invalid replacement format."""
        with pytest.raises(ValueError, match="Invalid replacement format"):
            ScenarioStep({"replacements": [{"pattern": r"test"}]})  # Missing replacement key

        with pytest.raises(ValueError, match="Invalid replacement format"):
            ScenarioStep({"replacements": ["invalid"]})  # Not a dict

    def test_invalid_regex_replacement_pattern(self):
        """Test error handling for invalid regex patterns in replacements."""
        with pytest.raises(ValueError, match="Invalid regex replacement pattern"):
            ScenarioStep({"replacements": [{"pattern": r"[unclosed", "replacement": "test"}]})

    def test_apply_replacements_no_replacements(self):
        """Test that apply_replacements returns original line when no replacements."""
        step = ScenarioStep({})
        original = "test log line"
        assert step.apply_replacements(original) == original

    def test_apply_replacements_with_static_text(self):
        """Test replacements with static text."""
        replacements = [
            {"pattern": r"user_\d+", "replacement": "user_anonymous"},
            {"pattern": r"password=\w+", "replacement": "password=***"},
        ]
        step = ScenarioStep({"replacements": replacements})

        log_line = "Login: user_123 password=secret123 successful"
        result = step.apply_replacements(log_line)
        expected = "Login: user_anonymous password=*** successful"
        assert result == expected

    def test_format_replacement_variables_sentence(self):
        """Test %s formatting variable for lorem sentence."""
        step = ScenarioStep({})
        result = step._format_replacement_variables("Message: %s")
        assert result.startswith("Message: ")
        assert len(result) > len("Message: ")
        # Should contain some lorem text
        assert any(char.isalpha() for char in result[9:])  # Skip "Message: " prefix

    def test_format_replacement_variables_random_number(self):
        """Test %n[x,y] formatting variable for random integers."""
        step = ScenarioStep({})
        result = step._format_replacement_variables("id_%n[100,200]_end")
        assert result.startswith("id_")
        assert result.endswith("_end")

        # Extract the number part
        number_str = result[3:-4]  # Remove "id_" and "_end"
        number = int(number_str)
        assert 100 <= number <= 200

    def test_format_replacement_variables_epoch(self):
        """Test %e formatting variable for epoch time."""
        import time

        before_time = int(time.time())

        step = ScenarioStep({})
        result = step._format_replacement_variables("timestamp_%e")

        after_time = int(time.time())

        assert result.startswith("timestamp_")
        epoch_str = result[10:]  # Remove "timestamp_" prefix
        epoch_time = int(epoch_str)
        assert before_time <= epoch_time <= after_time

    def test_format_replacement_variables_hex_lowercase(self):
        """Test %x[n] formatting variable for lowercase hexadecimal."""
        step = ScenarioStep({})
        result = step._format_replacement_variables("id_%x[8]")
        assert result.startswith("id_")
        hex_part = result[3:]
        assert len(hex_part) == 8
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_format_replacement_variables_hex_uppercase(self):
        """Test %X[n] formatting variable for uppercase hexadecimal."""
        step = ScenarioStep({})
        result = step._format_replacement_variables("ID_%X[4]")
        assert result.startswith("ID_")
        hex_part = result[3:]
        assert len(hex_part) == 4
        assert all(c in "0123456789ABCDEF" for c in hex_part)

    def test_format_replacement_variables_hex_different_lengths(self):
        """Test hex formatting variables with different lengths."""
        step = ScenarioStep({})

        # Test 2-character lowercase hex
        result2 = step._format_replacement_variables("short_%x[2]")
        hex_part2 = result2[6:]
        assert len(hex_part2) == 2
        assert all(c in "0123456789abcdef" for c in hex_part2)

        # Test 12-character uppercase hex
        result12 = step._format_replacement_variables("long_%X[12]")
        hex_part12 = result12[5:]
        assert len(hex_part12) == 12
        assert all(c in "0123456789ABCDEF" for c in hex_part12)

    def test_format_replacement_variables_random_string(self):
        """Test %r[n] formatting variable for random strings."""
        step = ScenarioStep({})
        result = step._format_replacement_variables("token_%r[8]")
        assert result.startswith("token_")
        random_part = result[6:]
        assert len(random_part) == 8
        # Should contain only letters and digits
        import string

        valid_chars = string.ascii_letters + string.digits
        assert all(c in valid_chars for c in random_part)

    def test_format_replacement_variables_guid(self):
        """Test %g formatting variable for GUID generation."""
        step = ScenarioStep({})
        result = step._format_replacement_variables("request_id=%g")
        assert result.startswith("request_id=")

        guid_part = result[11:]  # Remove "request_id=" prefix

        # GUID should match pattern: 8-4-4-4-12 hex digits
        guid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        import re

        assert re.match(guid_pattern, guid_part)

        # Check specific format components
        parts = guid_part.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8  # First part: 8 digits
        assert len(parts[1]) == 4  # Second part: 4 digits
        assert len(parts[2]) == 4  # Third part: 4 digits
        assert len(parts[3]) == 4  # Fourth part: 4 digits
        assert len(parts[4]) == 12  # Fifth part: 12 digits

        # All parts should be lowercase hex
        for part in parts:
            assert all(c in "0123456789abcdef" for c in part)

    def test_format_replacement_variables_guid_multiple(self):
        """Test multiple GUID generation produces unique values."""
        step = ScenarioStep({})

        # Generate multiple GUIDs
        guids = []
        for _ in range(5):
            result = step._format_replacement_variables("id_%g")
            guid_part = result[3:]  # Remove "id_" prefix
            guids.append(guid_part)

        # All GUIDs should be unique (very high probability)
        assert len(set(guids)) == len(guids)

        # All should match GUID format
        guid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        import re

        for guid in guids:
            assert re.match(guid_pattern, guid)

    def test_format_replacement_variables_custom_strings(self):
        """Test %S[key] formatting variable for custom strings."""
        custom_strings = {
            "names": ["Alice", "Bob", "Charlie"],
            "cities": ["New York", "London", "Tokyo"],
            "colors": ["red", "blue", "green"],
        }
        step = ScenarioStep({}, custom_strings)

        # Test with valid key
        result = step._format_replacement_variables("User %S[names] from %S[cities]")

        # Should contain one of the names and one of the cities
        contains_name = any(name in result for name in custom_strings["names"])
        contains_city = any(city in result for city in custom_strings["cities"])
        assert contains_name, (
            f"Result '{result}' should contain a name from {custom_strings['names']}"
        )
        assert contains_city, (
            f"Result '{result}' should contain a city from {custom_strings['cities']}"
        )

    def test_format_replacement_variables_custom_strings_missing_key(self):
        """Test %S[key] with missing key shows placeholder."""
        custom_strings = {"valid_key": ["value1", "value2"]}
        step = ScenarioStep({}, custom_strings)

        result = step._format_replacement_variables("Test %S[missing_key] placeholder")
        assert "[MISSING_KEY:missing_key]" in result

    def test_format_replacement_variables_custom_strings_empty(self):
        """Test %S[key] with no custom strings."""
        step = ScenarioStep({})  # No custom strings

        result = step._format_replacement_variables("Test %S[any_key] placeholder")
        assert "[MISSING_KEY:any_key]" in result

    def test_format_replacement_variables_custom_strings_multiple_same_key(self):
        """Test multiple %S[key] tokens with same key get different values."""
        custom_strings = {"items": ["apple", "banana", "cherry", "date", "elderberry"]}
        step = ScenarioStep({}, custom_strings)

        # Generate multiple results to test randomness
        results = []
        for _ in range(10):
            result = step._format_replacement_variables("%S[items] and %S[items]")
            results.append(result)

        # Just verify it's using valid items
        for result in results:
            for item in custom_strings["items"]:
                if item in result:
                    break
            else:
                raise AssertionError(
                    f"Result '{result}' should contain at least one item from {custom_strings['items']}"
                )

    def test_scenario_step_with_custom_strings(self):
        """Test ScenarioStep initialization with custom strings."""
        custom_strings = {
            "users": ["admin", "guest", "user123"],
            "actions": ["login", "logout", "view"],
        }
        step = ScenarioStep({"start_time": "0s"}, custom_strings)
        assert step.custom_strings == custom_strings

    def test_apply_replacements_with_custom_strings(self):
        """Test complete replacement flow with custom strings."""
        custom_strings = {
            "users": ["alice", "bob", "charlie"],
            "departments": ["engineering", "marketing", "sales"],
        }
        replacements = [
            {"pattern": r"user=\w+", "replacement": "user=%S[users]"},
            {"pattern": r"dept=\w+", "replacement": "dept=%S[departments]"},
            {"pattern": r"id=\d+", "replacement": "id=%n[1000,9999]"},
        ]
        step = ScenarioStep({"replacements": replacements}, custom_strings)

        log_line = "Login user=testuser dept=testdept id=123 successful"
        result = step.apply_replacements(log_line)

        # Should contain valid users and departments
        contains_user = any(user in result for user in custom_strings["users"])
        contains_dept = any(dept in result for dept in custom_strings["departments"])

        assert contains_user, (
            f"Result '{result}' should contain a user from {custom_strings['users']}"
        )
        assert contains_dept, (
            f"Result '{result}' should contain a department from {custom_strings['departments']}"
        )
        assert "testuser" not in result  # Original should be replaced
        assert "testdept" not in result  # Original should be replaced
        assert "123" not in result  # Original ID should be replaced

    def test_format_replacement_variables_multiple(self):
        """Test multiple formatting variables in one template."""
        step = ScenarioStep({})
        result = step._format_replacement_variables("user_%n[1,100]_session_%r[4]_time_%e")

        parts = result.split("_")
        assert parts[0] == "user"
        assert 1 <= int(parts[1]) <= 100
        assert parts[2] == "session"
        assert len(parts[3]) == 4
        assert parts[4] == "time"
        assert parts[5].isdigit()

    def test_apply_replacements_with_formatting_variables(self):
        """Test complete replacement flow with formatting variables."""
        replacements = [
            {"pattern": r"user_id=\d+", "replacement": "user_id=%n[1000,9999]"},
            {"pattern": r"session_token=\w+", "replacement": "session_token=%r[16]"},
            {"pattern": r"message=.*", "replacement": "message=%s"},
        ]
        step = ScenarioStep({"replacements": replacements})

        log_line = "Login user_id=123 session_token=abc123def message=original message here"
        result = step.apply_replacements(log_line)

        assert "user_id=" in result
        assert "session_token=" in result
        assert "message=" in result
        assert "123" not in result  # Original user_id should be replaced
        assert "abc123def" not in result  # Original session_token should be replaced
        assert "original message here" not in result  # Original message should be replaced


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
                    "parameters": {"format": "json", "number": 50},
                },
                {
                    "start_time": "60s",
                    "interval": "45s",
                    "iterations": 3,
                    "parameters": {"format": "apache_common", "number": 100},
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(scenario_data, f)
            f.flush()

            parser = ScenarioParser()
            scenario = parser.load_scenario(f.name)

            assert scenario["name"] == "Test Scenario"
            assert scenario["description"] == "Test description"
            assert len(scenario["steps"]) == 2
            assert scenario["steps"][0].start_time_seconds == 0.0
            assert scenario["steps"][0].iterations == 2
            assert scenario["steps"][1].start_time_seconds == 60.0
            assert scenario["steps"][1].iterations == 3

    def test_load_scenario_file_not_found(self):
        """Test error when scenario file doesn't exist."""
        parser = ScenarioParser()
        with pytest.raises(FileNotFoundError, match="Scenario file not found"):
            parser.load_scenario("nonexistent.yaml")

    def test_load_scenario_invalid_yaml(self):
        """Test error when YAML is invalid."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:\n  - bad indentation")
            f.flush()

            parser = ScenarioParser()
            with pytest.raises(ValueError, match="Invalid YAML"):
                parser.load_scenario(f.name)

    def test_load_scenario_missing_name(self):
        """Test error when scenario is missing name."""
        scenario_data = {"steps": [{"start_time": "0s"}]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(scenario_data, f)
            f.flush()

            parser = ScenarioParser()
            with pytest.raises(ValueError, match="Scenario must have a 'name' field"):
                parser.load_scenario(f.name)

    def test_load_scenario_missing_steps(self):
        """Test error when scenario is missing steps."""
        scenario_data = {"name": "Test"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(scenario_data, f)
            f.flush()

            parser = ScenarioParser()
            with pytest.raises(ValueError, match="Scenario must have a 'steps' array"):
                parser.load_scenario(f.name)

    def test_load_scenario_empty_steps(self):
        """Test error when steps array is empty."""
        scenario_data = {"name": "Test", "steps": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
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
            "bytes": 1024,
        }

        cmd = parser.build_flog_command_from_parameters(params)
        expected = [
            "flog",
            "-f",
            "json",
            "-n",
            "100",
            "-s",
            "30s",
            "--no-loop",
            "-d",
            "0.5s",
            "-r",
            "10",
            "-p",
            "1024",
        ]
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
            ScenarioStep({"start_time": "60s", "interval": "30s", "iterations": 3}),
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
