"""Input validation helpers (NFR-05).

Every route reads request data through these helpers so that wrong types,
missing fields and oversized text are rejected with a 400 instead of
crashing the server or reaching the database.
"""


def clean_str(value, max_len=None):
    """Return a stripped string, or "" if the value is not a string."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if max_len is not None and len(value) > max_len:
        return ""
    return value


def parse_int(value, minimum=None, maximum=None, default=None):
    """Return an int within range, or `default` if invalid."""
    if isinstance(value, bool):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None and number < minimum:
        return default
    if maximum is not None and number > maximum:
        return default
    return number


def is_vehicle_id(value):
    """Vehicle IDs: 3-20 characters, letters, digits and dashes only."""
    if not isinstance(value, str) or not 3 <= len(value) <= 20:
        return False
    return all(c.isalnum() or c == "-" for c in value)
