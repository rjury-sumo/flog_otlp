"""Tests for CLI strings file functionality."""

import tempfile

import pytest
import yaml

from flog_otlp.cli import load_strings_file


class TestLoadStringsFile:
    """Tests for load_strings_file function."""

    def test_load_strings_file_success(self):
        """Test successful strings file loading."""
        strings_data = {
            "names": ["Alice", "Bob", "Charlie"],
            "cities": ["New York", "London", "Tokyo"],
            "colors": ["red", "blue", "green", "yellow"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(strings_data, f)
            f.flush()

            result = load_strings_file(f.name)

            assert result == strings_data
            assert len(result["names"]) == 3
            assert len(result["cities"]) == 3
            assert len(result["colors"]) == 4

    def test_load_strings_file_not_found(self):
        """Test error when strings file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Strings file not found"):
            load_strings_file("nonexistent.yaml")

    def test_load_strings_file_invalid_yaml(self):
        """Test error when YAML is invalid."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:\n  - bad indentation")
            f.flush()

            with pytest.raises(ValueError, match="Invalid YAML"):
                load_strings_file(f.name)

    def test_load_strings_file_not_dict(self):
        """Test error when YAML is not a dictionary."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(["not", "a", "dict"], f)
            f.flush()

            with pytest.raises(ValueError, match="must contain a YAML object with string arrays"):
                load_strings_file(f.name)

    def test_load_strings_file_value_not_list(self):
        """Test error when value is not a list."""
        strings_data = {"names": ["Alice", "Bob"], "invalid": "not a list"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(strings_data, f)
            f.flush()

            with pytest.raises(ValueError, match="Key 'invalid' must be a list of strings"):
                load_strings_file(f.name)

    def test_load_strings_file_item_not_string(self):
        """Test error when list item is not a string."""
        strings_data = {"names": ["Alice", "Bob"], "invalid": ["valid", 123, "also_valid"]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(strings_data, f)
            f.flush()

            with pytest.raises(ValueError, match="Key 'invalid', item 1: expected string, got int"):
                load_strings_file(f.name)

    def test_load_strings_file_empty_list(self):
        """Test error when list is empty."""
        strings_data = {"names": ["Alice", "Bob"], "empty": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(strings_data, f)
            f.flush()

            with pytest.raises(ValueError, match="Key 'empty' must contain at least one string"):
                load_strings_file(f.name)

    def test_load_strings_file_mixed_valid_content(self):
        """Test loading with various valid string types."""
        strings_data = {
            "short": ["a", "b"],
            "long": ["This is a longer string", "Another long string"],
            "mixed": ["short", "A much longer string with spaces and punctuation!", "123"],
            "unicode": ["café", "naïve", "résumé"],
            "special": ["@#$%", "user@domain.com", "http://example.com"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(strings_data, f)
            f.flush()

            result = load_strings_file(f.name)

            assert result == strings_data
            assert len(result["short"]) == 2
            assert len(result["long"]) == 2
            assert len(result["mixed"]) == 3
            assert len(result["unicode"]) == 3
            assert len(result["special"]) == 3
