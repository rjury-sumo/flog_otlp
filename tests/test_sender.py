"""Tests for sender module."""

from unittest.mock import Mock, patch

from flog_otlp.sender import OTLPLogSender


class TestOTLPLogSender:
    """Test OTLPLogSender class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sender = OTLPLogSender()

    def test_init_defaults(self):
        """Test initialization with default values."""
        assert self.sender.endpoint == "http://localhost:4318/v1/logs"
        assert self.sender.service_name == "flog-generator"
        assert self.sender.delay == 0.1
        assert self.sender.log_format == "apache_common"
        assert self.sender.otlp_headers == {}
        assert self.sender.otlp_attributes == {}
        assert self.sender.telemetry_attributes == {}

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        custom_headers = {"Authorization": "Bearer token"}
        custom_attributes = {"env": "production"}
        custom_telemetry = {"app": "web-server"}

        sender = OTLPLogSender(
            endpoint="https://custom.endpoint/logs",
            service_name="custom-service",
            delay=0.5,
            otlp_headers=custom_headers,
            otlp_attributes=custom_attributes,
            telemetry_attributes=custom_telemetry,
            log_format="json",
        )

        assert sender.endpoint == "https://custom.endpoint/logs"
        assert sender.service_name == "custom-service"
        assert sender.delay == 0.5
        assert sender.log_format == "json"
        assert sender.otlp_headers == custom_headers
        assert sender.otlp_attributes == custom_attributes
        assert sender.telemetry_attributes == custom_telemetry

    def test_parse_flog_line_json(self):
        """Test parsing JSON flog line."""
        json_line = '{"message": "test message", "level": "ERROR", "time": "2023-01-01T12:00:00Z"}'
        result = self.sender.parse_flog_line(json_line)

        assert result["message"] == "test message"
        assert result["level"] == "ERROR"
        assert result["timestamp"] == "2023-01-01T12:00:00Z"

    def test_parse_flog_line_plain_text(self):
        """Test parsing plain text flog line."""
        text_line = '192.168.1.1 - - [01/Jan/2023:12:00:00 +0000] "GET / HTTP/1.1" 200 1234'
        result = self.sender.parse_flog_line(text_line)

        assert result["message"] == text_line
        assert result["level"] == "INFO"
        assert "timestamp" in result

    def test_convert_attribute_value_string(self):
        """Test attribute value conversion for strings."""
        result = self.sender._convert_attribute_value("test")
        assert result == {"stringValue": "test"}

    def test_convert_attribute_value_boolean(self):
        """Test attribute value conversion for booleans."""
        result = self.sender._convert_attribute_value(True)
        assert result == {"boolValue": True}

    def test_convert_attribute_value_integer(self):
        """Test attribute value conversion for integers."""
        result = self.sender._convert_attribute_value(42)
        assert result == {"intValue": 42}

    def test_convert_attribute_value_float(self):
        """Test attribute value conversion for floats."""
        result = self.sender._convert_attribute_value(3.14)
        assert result == {"doubleValue": 3.14}

    def test_get_severity_number(self):
        """Test severity number mapping."""
        assert self.sender.get_severity_number("DEBUG") == 5
        assert self.sender.get_severity_number("INFO") == 9
        assert self.sender.get_severity_number("WARNING") == 13
        assert self.sender.get_severity_number("ERROR") == 17
        assert self.sender.get_severity_number("UNKNOWN") == 9  # Default

    def test_create_otlp_payload(self):
        """Test OTLP payload creation."""
        log_entry = {
            "message": "test message",
            "level": "INFO",
            "timestamp": "2023-01-01T12:00:00Z",
        }

        payload = self.sender.create_otlp_payload(log_entry)

        assert "resourceLogs" in payload
        resource_logs = payload["resourceLogs"][0]
        assert "resource" in resource_logs
        assert "scopeLogs" in resource_logs

        log_record = resource_logs["scopeLogs"][0]["logRecords"][0]
        assert log_record["body"]["stringValue"] == "test message"
        assert log_record["severityText"] == "INFO"

    def test_create_otlp_payload_attributes(self):
        """Test OTLP payload creation includes correct attributes."""
        sender = OTLPLogSender(log_format="json")
        log_entry = {
            "message": "test message",
            "level": "INFO",
            "timestamp": "2023-01-01T12:00:00Z",
        }

        payload = sender.create_otlp_payload(log_entry)
        log_record = payload["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]

        # Check log attributes
        attributes = {attr["key"]: attr["value"] for attr in log_record["attributes"]}
        assert "log_source" in attributes
        assert attributes["log_source"]["stringValue"] == "flog"
        assert "log_type" in attributes
        assert attributes["log_type"]["stringValue"] == "json"

    @patch("flog_otlp.sender.requests.Session")
    def test_send_log_success(self, mock_session_class):
        """Test successful log sending."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = OTLPLogSender()
        sender.session = mock_session
        payload = {"test": "payload"}

        sender.send_log(payload)

        mock_session.post.assert_called_once()
        args, kwargs = mock_session.post.call_args
        assert args[0] == sender.endpoint
        assert kwargs["json"] == payload
