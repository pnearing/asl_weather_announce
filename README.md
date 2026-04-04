# ASL Weather Announce

A Python-based weather announcement system for [AllStarLinkv3](https://www.allstarlink.org/) (ASLv3) amateur radio networks. Fetches current weather conditions and broadcasts spoken weather reports through ASL nodes using text-to-speech. This has been tested on AllStarLink V3.1.2, running Debian Trixie.

## Features

- **Dual Location Support**: Look up locations by postal/ZIP code or specify exact latitude/longitude coordinates
- **Free Weather Data**: Uses Open-Meteo API (no API key required)
- **Smart Geocoding**: Multi-service postal code lookup with automatic failover (Zippopotam.us → OpenStreetMap Nominatim)
- **TTS-Optimized Output**: Natural language weather descriptions designed for speech synthesis
- **Time & Date Announcements**: Optional current time and date announcements with timezone support
- **Persistent Caching**: Disk-based caching for location lookups to reduce API calls
- **Flexible Configuration**: INI file configuration with CLI override support
- **Voice Selection**: Configurable TTS voices via asl-tts integration
- **Dry-Run Mode**: Test mode to preview announcements without broadcasting
- **Comprehensive Logging**: File or console logging with configurable log levels

## Installation

### Debian Package (Recommended)

For Debian Trixie and compatible systems (Ubuntu 24.04+, etc.), install via the `.deb` package:

```bash
# Download the latest .deb from the releases page
wget https://github.com/AllStarLink/asl_weather_announce/releases/latest/download/asl-weather-announce_*.deb

# Install the package
sudo dpkg -i asl-weather-announce_*.deb

# Install any missing dependencies
sudo apt-get install -f
```

### Manual Installation

#### Prerequisites
- Root or `asterisk` user privileges (for ASL integration)
- `asl-tts` command-line tool for text-to-speech

### Python Dependencies

Note: AllStarLink V3 systems already have Python 3.6+ and the `requests` library available.

```bash
pip install requests
```

### System Dependencies

```bash
# Install asl-tts (method depends on your ASL distribution)
sudo apt install asl-tts  # or equivalent for your system
```

## Quick Start

1. **Copy the example configuration:**
   ```bash
   sudo cp config.ini.example /etc/asl_weather.conf
   ```

2. **Edit the configuration** with your location and node number:
   ```bash
   sudo nano /etc/asl_weather.conf
   ```

3. **Run the script:**
   ```bash
   sudo asl_weather
   ```

## Configuration

The configuration file uses INI format with the following sections:

### `[asl_weather]` - General Settings

| Option | Description | Default |
|--------|-------------|---------|
| `log_file` | Path to log file (optional) | console output |
| `say_time` | Announce current time (`true`/`false`) | `false` |
| `say_date` | Announce current date (`true`/`false`) | `false` |
| `timezone` | IANA timezone name (e.g., `America/Toronto`) | system local time |

### `[location]` - Location Settings

| Option | Description | Required |
|--------|-------------|----------|
| `postal_code` | Postal or ZIP code | Yes (unless using lat/lon) |
| `country_code` | Country identifier* | Yes (unless using lat/lon) |
| `latitude` | Decimal latitude (-90 to 90) | No |
| `longitude` | Decimal longitude (-180 to 180) | No |
| `location_name` | Override location name for TTS | No |

\* Country code accepts: 2-letter (CA), 3-letter (CAN), numeric (124), or full name (Canada)

### `[asl]` - ASL Node Settings

| Option | Description | Required |
|--------|-------------|----------|
| `node_number` | Your ASL node number | Yes |

### `[asl-tts]` - TTS Voice Settings

| Option | Description | Default |
|--------|-------------|---------|
| `voice` | Voice file name (e.g., `en_GB-alan-low.onnx`) | system default |
| `voice_dir` | Directory containing voice files | `/var/lib/piper-tts` |

### Example Configuration

```ini
[asl_weather]
log_file = /var/log/asl_weather.log
say_time = true
say_date = true
timezone = America/Toronto

[location]
postal_code = N6A 3K7
country_code = CA

[asl]
node_number = 12345

[asl-tts]
voice = en_GB-alan-low.onnx
```

### Configuration with Coordinates (No Postal Code)

```ini
[location]
# Skip postal code lookup by providing direct coordinates
latitude = 43.6532
longitude = -79.3832
location_name = Toronto, Ontario  # Optional: skip reverse geocoding

country_code = CA  # Still used as fallback
```

## Usage

### Basic Usage

```bash
# Use default config file (/etc/asl_weather.conf)
sudo asl_weather

# Specify custom config file
sudo asl_weather --config /path/to/custom.conf
```

### Command Line Overrides

All config file options can be overridden via command line:

```bash
# Override location
sudo asl_weather --postal-code N6A3K7 --country-code CA

# Override node number and voice
sudo asl_weather -n 54321 -v en_US-amy-low.onnx

# Enable time and date announcements
sudo asl_weather --say-time --say-date

# Full example with multiple overrides
sudo asl_weather \
    -p N6A3K7 \
    -c CA \
    -n 12345 \
    -v en_GB-alan-low.onnx \
    --say-time \
    --say-date \
    -l /var/log/weather.log
```

### Testing (Dry-Run Mode)

Preview the announcement text without broadcasting:

```bash
asl_weather --dry-run
```

Output example:

```text
Today is April 4, 2026. The current time is 7 15 AM. Currently in London, Ontario it is 8 degrees Celsius with partly cloudy.
```

### Command Line Options

| Short | Long | Description |
|-------|------|-------------|
| `-C` | `--config` | Path to configuration file |
| `-p` | `--postal-code` | Postal/ZIP code to lookup |
| `-c` | `--country-code` | Country code (2-letter, 3-letter, numeric, or full name) |
| `-n` | `--node-number` | ASL node number |
| `-v` | `--voice` | TTS voice file name |
| `-l` | `--log-file` | Path to log file |
| `-t` | `--say-time` | Announce current time |
| `-T` | `--no-say-time` | Do not announce current time |
| `-d` | `--say-date` | Announce current date |
| `-D` | `--no-say-date` | Do not announce current date |
| | `--dry-run` | Print text only, don't broadcast |

## Location Specification Methods

### Method 1: Postal/ZIP Code (Recommended)

Uses postal code lookup with automatic geocoding:

```ini
[location]
postal_code = N6A 3K7
country_code = CA
```

- Uses Zippopotam.us API first (fast, lightweight)
- Falls back to OpenStreetMap Nominatim if needed
- Results are cached to disk for performance

### Method 2: Direct Coordinates

For locations without postal codes or mobile stations:

```ini
[location]
latitude = 43.6532
longitude = -79.3832
location_name = Toronto, Ontario  # Optional override
```

- Bypasses postal code lookup entirely
- If `location_name` is provided, reverse geocoding is skipped
- If `location_name` is omitted, performs reverse geocoding to get city name

## Project Structure

```
asl_weather_announce/
├── asl_weather                    # Main entry point
├── config.ini.example         # Example configuration file
├── get_location/              # Location lookup package
│   ├── postal_lookup.py       # Postal code geocoding
│   ├── country_codes.py       # Country code normalization
│   └── exceptions.py          # Custom exceptions
├── get_weather/               # Weather lookup package
│   ├── weather_lookup.py      # Open-Meteo API client
│   └── exceptions.py          # Custom exceptions
├── get_location_example_usage.py
└── get_weather_example_usage.py
```

## API Information

### Location Services

**Primary: Zippopotam.us**
- URL: <https://api.zippopotam.us/{country}/{postalcode}>
- Free, no API key required
- Fast and lightweight

**Fallback: OpenStreetMap Nominatim**
- URL: <https://nominatim.openstreetmap.org/search>
- Free, attribution required
- Comprehensive global coverage

### Weather Service

**Open-Meteo**
- URL: <https://api.open-meteo.com/v1/forecast>
- Free, unlimited access, no API key required
- Data source: ECMWF (European Centre for Medium-Range Weather Forecasts)

## Caching

Location lookups are cached to reduce API calls and improve performance:

- **Root users**: `/var/cache/asl_weather_announce/postal_cache.json`
- **Regular users**: `~/.cache/asl_weather_announce/postal_cache.json`

Cache entries are persistent across script runs.

## Troubleshooting

### Permission Denied

```
This script must be run as root or the asterisk user.
```

**Solution**: Use `sudo` or run as the `asterisk` user:
```bash
sudo asl_weather
```

### Missing Dependencies

```
Missing required dependencies:
  - requests (Python module)
  - asl-tts (system binary)
```

**Solution**: Install missing dependencies:
```bash
pip install requests
sudo apt install asl-tts  # or equivalent
```

### Voice Not Found

```
Warning: Voice 'en_GB-alan-low.onnx' not found in /var/lib/piper-tts
```

**Solution**: Check available voices and update configuration:
```bash
ls /var/lib/piper-tts/
```

### Postal Code Not Found

```
Could not find location for postal code 'XXXXX' in country 'XX'
```

**Solution**:

- Verify the postal code is valid
- Try using direct latitude/longitude coordinates instead
- Check network connectivity

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LOG_LEVEL` | Set logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO |

Example:
```bash
LOG_LEVEL=DEBUG sudo asl_weather --dry-run
```

## Building from Source

### Debian Package Build

To build the Debian package locally:

```bash
# Install build dependencies
sudo apt-get install build-essential debhelper debhelper-compat dh-python fakeroot python3-all python3-setuptools devscripts

# Build the package
make deb

# Or use dpkg-buildpackage directly
dpkg-buildpackage -us -uc -b
```

The built `.deb` package will be in the parent directory.

### Source Archive

To create a source tarball:

```bash
make source
```

## CI/CD

This project uses automated CI/CD pipelines to build and release packages:

### GitHub Actions

The `.github/workflows/release.yml` workflow automatically:
- Builds Debian packages for Trixie on every tag push
- Creates source tarballs
- Publishes releases with `.deb` and `.tar.gz` artifacts

Trigger a release by pushing a tag:
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Forgejo

The `.forgejo/workflows/release.yml` workflow provides the same functionality for Forgejo-hosted repositories.

## License

This project is licensed under the terms specified in the LICENSE file.

## Author

Peter Nearing - me@peternearing.ca

## Version

1.0.0
