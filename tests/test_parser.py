"""Tests for parser module."""

from flog_otlp.parser import parse_key_value_pairs


def test_parse_key_value_pairs_empty():
    """Test parsing empty list returns empty dict."""
    result = parse_key_value_pairs([])
    assert result == {}


def test_parse_key_value_pairs_none():
    """Test parsing None returns empty dict."""
    result = parse_key_value_pairs(None)
    assert result == {}


def test_parse_key_value_pairs_string_values():
    """Test parsing string values."""
    result = parse_key_value_pairs(["env=production", "region=us-east-1"])
    expected = {"env": "production", "region": "us-east-1"}
    assert result == expected


def test_parse_key_value_pairs_boolean_values():
    """Test parsing boolean values."""
    result = parse_key_value_pairs(["debug=true", "enabled=false"])
    expected = {"debug": True, "enabled": False}
    assert result == expected


def test_parse_key_value_pairs_numeric_values():
    """Test parsing numeric values."""
    result = parse_key_value_pairs(["port=8080", "timeout=30.5"])
    expected = {"port": 8080, "timeout": 30.5}
    assert result == expected


def test_parse_key_value_pairs_quoted_values():
    """Test parsing quoted values."""
    result = parse_key_value_pairs(['"env"="production with spaces"', "'region'='us-east-1'"])
    expected = {"env": "production with spaces", "region": "us-east-1"}
    assert result == expected


def test_parse_key_value_pairs_malformed(caplog):
    """Test parsing malformed entries logs warnings."""
    result = parse_key_value_pairs(["malformed", "valid=value"])
    expected = {"valid": "value"}
    assert result == expected
    assert "Ignoring malformed attribute 'malformed'" in caplog.text
