# Contributing to ASL Weather Announce

Thank you for your interest in contributing to ASL Weather Announce! This document provides guidelines and standards for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Documentation Standards](#documentation-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)


## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your feature or bug fix
4. Make your changes following our code style guidelines
5. Test your changes thoroughly
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.8 or higher
- `git` for version control
- Root / asterisk user access (for testing with `asl-tts`)

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/asl_weather_announce.git
cd asl_weather_announce

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r developer_requirements.txt
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=get_weather --cov=get_location

# Run specific test file
python -m pytest tests/test_weather_lookup.py
```

### Dry Run Testing

Use dry-run mode to test without requiring root privileges or `asl-tts`:

```bash
python asl_weather --dry-run -p N6A3K7 -c CA -n 12345
```

## Code Style

### Python Style Guide

We follow PEP 8 with the following specific conventions:

#### Line Length
- Maximum line length: **100 characters**
- For docstrings and comments: **72 characters**

#### Indentation
- Use **4 spaces** per indentation level
- Never use tabs

#### Naming Conventions

| Type | Convention | Example |
| --- | --- | --- |
| Modules | lowercase with underscores | `weather_lookup.py` |
| Classes | CapWords | `CurrentWeatherResult` |
| Functions | lowercase with underscores | `get_current_weather()` |
| Constants | UPPERCASE_WITH_UNDERSCORES | `DEFAULT_CONFIG_PATH` |
| Variables | lowercase with underscores | `temperature_unit` |
| Private attributes | leading underscore | `_format_temp()` |

#### Imports

Organize imports in this order, separated by blank lines:

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from get_location import PostalLookup
```

### Documentation Standards

All modules, classes, and functions must have docstrings following the **Google Style**:

```python
def get_current_weather(
    *,
    city: str,
    latitude: float,
    longitude: float,
    temperature_unit: TemperatureUnit = "C",
) -> CurrentWeatherResult:
    """Fetch current weather conditions using latitude/longitude.

    Parameters:
        city: Human-readable city name for output text.
        latitude: Decimal latitude.
        longitude: Decimal longitude.
        temperature_unit: "C" or "F".

    Returns:
        CurrentWeatherResult with weather information.

    Raises:
        ValueError: Bad arguments.
        NetworkError: Network connectivity issues.
        WeatherLookupError: General weather lookup issues.

    Example:
        >>> result = get_current_weather(
        ...     city="London",
        ...     latitude=42.98,
        ...     longitude=-81.25,
        ... )
    """
```

#### Docstring Requirements

- First line: Brief summary (one line, no period needed if single line)
- Blank line
- Detailed description (if needed)
- `Parameters:` section with type info
- `Returns:` section with type info
- `Raises:` section listing all exceptions
- `Example:` section with doctests where applicable

### Type Hints

Use type hints for all function parameters and return values:

```python
from typing import Optional, Literal

TemperatureUnit = Literal["C", "F"]

def format_temperature(
    value: float,
    unit: TemperatureUnit,
    precision: Optional[int] = None
) -> str:
    ...
```

### Error Handling

- Use specific exception classes from `exceptions.py`
- Chain exceptions with `from` when re-raising
- Log errors before exiting with non-zero status

```python
try:
    result = lookup.lookup(postal_code, country_code)
except NetworkError as e:
    logger.error(f"Network error during lookup: {e}")
    sys.exit(1)
except PostalLookupError as e:
    logger.error(f"Lookup failed: {e}")
    sys.exit(1)
```

### Configuration Handling

- Load from config file first, then apply CLI overrides
- Validate all configuration values early
- Provide helpful error messages with examples

```python
def load_config(config_path: str) -> Dict[str, Any]:
    config = {
        "temperature_unit": "C",  # sensible default
    }
    # ... load from file
    return config
```

### Logging

- Use the `logging` module, not `print()`
- Use appropriate log levels:
  - `DEBUG`: Detailed information for debugging
  - `INFO`: Confirmation that things are working, progress updates
  - `WARNING`: Something unexpected but handled
  - `ERROR`: Serious problem, often followed by exit
- Include context in log messages

```python
logger.debug(f"Resolved location: {location_data['city']}")
logger.info("Weather announcement sent successfully")
logger.warning(f"Voice '{voice}' not found, using default")
logger.error(f"Invalid coordinates: {e}")
```

## Testing

### Test Requirements

- All new features must include tests
- Bug fixes must include regression tests
- Maintain or improve code coverage

### Test Organization

```text
tests/
├── __init__.py
├── test_weather_lookup.py
├── test_postal_lookup.py
├── test_exceptions.py
└── conftest.py          # Shared fixtures
```

### Writing Tests

```python
import pytest
from get_weather import get_current_weather, CurrentWeatherResult

def test_weather_lookup_success(mock_api_response):
    """Test successful weather lookup."""
    result = get_current_weather(
        city="London",
        latitude=42.98,
        longitude=-81.25,
    )
    assert isinstance(result, CurrentWeatherResult)
    assert result.temperature is not None

def test_weather_lookup_invalid_coordinates():
    """Test that invalid coordinates raise ValueError."""
    with pytest.raises(ValueError):
        get_current_weather(
            city="Invalid",
            latitude=999,
            longitude=-81.25,
        )
```

## Submitting Changes

### Pull Request Process

1. Update the README.md with details of changes if applicable
2. Update the TODO.md to mark items as completed
3. Ensure all tests pass
4. Update documentation as needed
5. Submit PR with clear description of changes
6. Link any related issues

### Code Review

All submissions require review. Reviewers will check:

- Code follows style guidelines
- Tests are included and passing
- Documentation is updated
- No breaking changes without justification

## Release Process

1. Update version in `__init__.py`, `asl_weather`, and module files, IE:
   - `get_location/postal_lookup.py`
   - `get_weather/weather_lookup.py`
2. Update CHANGELOG.md
3. Tag release: `git tag -a v1.2.0 -m "Version 1.2.0"`
4. Push tags: `git push origin v1.2.0`

## Questions?

If you have questions about contributing, please:

1. Check existing documentation
2. Search closed issues and PRs
3. Open a new issue with the `question` label

Thank you for contributing to ASL Weather Announce!
