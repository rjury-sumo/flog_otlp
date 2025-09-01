"""Parser utilities for flog-otlp."""

import logging


def parse_key_value_pairs(values_list):
    """Parse key=value pairs from command line arguments"""
    result = {}
    logger = logging.getLogger("otlp_log_sender.parser")

    if not values_list:
        return result

    for item in values_list:
        if "=" not in item:
            logger.warning(f"Ignoring malformed attribute '{item}' (expected format: key=value)")
            continue

        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Remove surrounding quotes from key if present
        if (key.startswith('"') and key.endswith('"')) or (
            key.startswith("'") and key.endswith("'")
        ):
            key = key[1:-1]

        # Remove surrounding quotes from value if present
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        # Convert value to appropriate type
        if value.lower() == "true":
            result[key] = True
        elif value.lower() == "false":
            result[key] = False
        else:
            # Try to parse as integer
            try:
                result[key] = int(value)
            except ValueError:
                # Try to parse as float
                try:
                    result[key] = float(value)
                except ValueError:
                    # Keep as string
                    result[key] = value

    return result
