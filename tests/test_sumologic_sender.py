"""Tests for SumoLogicSender class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flog_otlp.sender import SumoLogicSender


class TestSumoLogicSender:
    """Test cases for SumoLogicSender class."""

    def test_init_defaults(self):
        """Test SumoLogicSender initialization with default values."""
        sender = SumoLogicSender(endpoint="https://endpoint.sumologic.com/receiver/v1/http/...")

        assert sender.endpoint == "https://endpoint.sumologic.com/receiver/v1/http/..."
        assert sender.delay == 0.1
        assert sender.category is None
        assert sender.name is None
        assert sender.host is None
        assert sender.fields == {}

    def test_init_custom_values(self):
        """Test SumoLogicSender initialization with custom values."""
        fields = {"environment": "production", "region": "us-east-1"}
        sender = SumoLogicSender(
            endpoint="https://endpoint.sumologic.com/receiver/v1/http/...",
            delay=0.5,
            category="test/category",
            name="test-source",
            host="test-host",
            fields=fields,
        )

        assert sender.endpoint == "https://endpoint.sumologic.com/receiver/v1/http/..."
        assert sender.delay == 0.5
        assert sender.category == "test/category"
        assert sender.name == "test-source"
        assert sender.host == "test-host"
        assert sender.fields == fields

    @patch("flog_otlp.sender.requests.Session")
    def test_send_log_success(self, mock_session_class):
        """Test successful log sending to Sumo Logic."""
        # Setup mock
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = SumoLogicSender(endpoint="https://endpoint.sumologic.com/receiver/v1/http/...")
        sender.send_log("test log line")

        # Verify POST was called
        assert mock_session.post.called
        call_args = mock_session.post.call_args

        # Check endpoint
        assert call_args[0][0] == "https://endpoint.sumologic.com/receiver/v1/http/..."

        # Check data
        assert call_args[1]["data"] == b"test log line"

        # Check headers
        headers = call_args[1]["headers"]
        assert headers["Content-Type"] == "text/plain"
        assert "X-Sumo-Category" not in headers  # No category was set

    @patch("flog_otlp.sender.requests.Session")
    def test_send_log_with_metadata_headers(self, mock_session_class):
        """Test log sending with Sumo Logic metadata headers."""
        # Setup mock
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        fields = {"env": "prod", "app": "test"}
        sender = SumoLogicSender(
            endpoint="https://endpoint.sumologic.com/receiver/v1/http/...",
            category="test/logs",
            name="test-source",
            host="test-host",
            fields=fields,
        )
        sender.send_log("test log line")

        # Verify headers
        call_args = mock_session.post.call_args
        headers = call_args[1]["headers"]

        assert headers["Content-Type"] == "text/plain"
        assert headers["X-Sumo-Category"] == "test/logs"
        assert headers["X-Sumo-Name"] == "test-source"
        assert headers["X-Sumo-Host"] == "test-host"
        assert headers["X-Sumo-Fields"] == "env=prod,app=test"

    @patch("flog_otlp.sender.requests.Session")
    def test_send_log_failure(self, mock_session_class):
        """Test log sending failure handling."""
        # Setup mock
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = SumoLogicSender(endpoint="https://endpoint.sumologic.com/receiver/v1/http/...")

        # Should not raise exception, just log error
        sender.send_log("test log line")

        assert mock_session.post.called

    def test_obfuscate_endpoint(self):
        """Test endpoint obfuscation for logging."""
        sender = SumoLogicSender(endpoint="https://endpoint.sumologic.com/receiver/v1/http/test")

        # Test with typical Sumo Logic endpoint
        endpoint = (
            "https://collectors.au.sumologic.com/receiver/v1/http/ZaVnC4iD0FoV8dGHjklmM-LhA=="
        )
        obfuscated = sender._obfuscate_endpoint(endpoint)
        assert obfuscated == "https://collectors.au.sumologic.com/receiver/v1/http/ZaVnC***LhA=="

        # Test with short token (should not obfuscate if <= 10 chars)
        endpoint_short = "https://collectors.au.sumologic.com/receiver/v1/http/short"
        obfuscated_short = sender._obfuscate_endpoint(endpoint_short)
        assert obfuscated_short == endpoint_short

        # Test with no path (should return as-is)
        endpoint_no_path = "https://collectors.au.sumologic.com"
        obfuscated_no_path = sender._obfuscate_endpoint(endpoint_no_path)
        assert obfuscated_no_path == endpoint_no_path
