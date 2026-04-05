# ASL Weather Announce

A Python-based weather announcement system for [AllStarLinkv3](https://www.allstarlink.org/) (ASLv3) amateur radio networks. Fetches current weather conditions and broadcasts spoken weather reports through ASL nodes using text-to-speech. This has been tested on AllStarLink V3.1.2, running Debian Trixie.

## Features

- **Dual Location Support**: Look up locations by postal/ZIP code or specify exact latitude/longitude coordinates
- **Free Weather Data**: Uses Open-Meteo API (no API key required)
- **Smart Geocoding**: Multi-service postal code lookup with automatic failover (Zippopotam.us → OpenStreetMap Nominatim)
- **TTS-Optimized Output**: Natural language weather descriptions designed for speech synthesis
- **Time & Date Announcements**: Optional current time and date announcements with timezone support
- **Pre/Post Announcements**: Configurable text to announce before and after the main weather report
- **LRU Caching**: Sized-based LRU cache for location lookups with configurable size
- **Offline Mode**: Announce time/date only without weather API calls (useful for network outages)
- **Circuit Breaker Protection**: Automatic circuit breakers prevent cascading failures when APIs are down
- **API Metrics**: Tracks API response times and success rates for monitoring
- **Persistent Storage**: Cache survives script restarts
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

### Log Directory Setup (Manual Install)

When installing manually (not via .deb package), create the log directory with proper permissions for the `asterisk` user:

```bash
# Create log directory
sudo mkdir -p /var/log/asl_weather

# Set permissions: owner root, group asterisk, writable by group
sudo chown root:asterisk /var/log/asl_weather
sudo chmod 775 /var/log/asl_weather

# Create the log file with asterisk group ownership
sudo touch /var/log/asl_weather/asl_weather.log
sudo chown root:asterisk /var/log/asl_weather/asl_weather.log
sudo chmod 664 /var/log/asl_weather/asl_weather.log
```

**Note:** These steps are handled automatically when installing via the Debian package.

### Log Rotation Setup (Manual Install)

When installing manually, also set up log rotation to prevent the log file from growing indefinitely:

```bash
# Copy the logrotate configuration
sudo cp system/asl-weather-announce.logrotate /etc/logrotate.d/asl-weather-announce
```

This rotates logs daily, keeping 14 days of compressed backups. Requires the `logrotate` package (typically installed by default on Debian systems).

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
| -------- | ------------- | --------- |
| `log_file` | Path to log file (optional) | console output |
| `say_time` | Announce current time (`true`/`false`) | `false` |
| `say_date` | Announce current date (`true`/`false`) | `false` |
| `timezone` | IANA timezone name (e.g., `America/Toronto`) | system local time |
| `temperature_unit` | Temperature unit (`C` or `F`) | `C` |
| `offline` | Offline mode - time/date only (`true`/`false`) | `false` |
| `cache_size` | Location cache size (entries) | `100` |
| `pre_announcement` | Text to announce before the main content | none |
| `post_announcement` | Text to announce after the main content | none |

### `[location]` - Location Settings

| Option | Description | Required |
| -------- | ------------- | ---------- |
| `postal_code` | Postal or ZIP code | Yes (unless using lat/lon) |
| `country_code` | Country identifier* | Yes (unless using lat/lon) |
| `latitude` | Decimal latitude (-90 to 90) | No |
| `longitude` | Decimal longitude (-180 to 180) | No |
| `location_name` | Override location name for TTS | No |

\* Country code accepts: 2-letter (CA), 3-letter (CAN), numeric (124), or full name (Canada)

### `[asl]` - ASL Node Settings

| Option | Description | Required |
| -------- | ------------- | ---------- |
| `node_number` | Your ASL node number | Yes |

### `[asl-tts]` - TTS Voice Settings

| Option | Description | Default |
| -------- | ------------- | --------- |
| `voice` | Voice file name (e.g., `en_GB-alan-low.onnx`) | system default |
| `voice_dir` | Directory containing voice files | `/var/lib/piper-tts` |

### Example Configuration

```ini
[asl_weather]
log_file = /var/log/asl_weather/asl_weather.log
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

### Configuration with Offline Mode

For network outages or testing without weather API calls:

```ini
[asl_weather]
# Only announce time/date, skip all API calls
offline = true
say_time = true
say_date = true
timezone = America/Toronto
```

### Configuration with Custom Cache Size

For mobile nodes that visit many locations, increase the cache size:

```ini
[asl_weather]
# Increase cache for mobile operation (default is 100)
cache_size = 500

[location]
postal_code = N6A 3K7
country_code = CA
```

### Configuration with Pre/Post Announcements

Add custom text before and after the weather announcement:

```ini
[asl_weather]
# Announce custom text before the weather
pre_announcement = Attention please

# Announce custom text after the weather
post_announcement = Thank you for listening, 73
```

Output example:

```text
Attention please. Currently in London, Ontario it is 8 degrees Celsius with partly cloudy. Thank you for listening, 73.
```

Or via command line:

```bash
sudo asl_weather -b "Attention please" -a "73 and good bye"
```

### Configuration with Direct Coordinates

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
Today is April 4, 2026. The current time is 7 15 AM. Currently in London, Ontario it is 8 degrees Celsius and partly cloudy.
```

### Command Line Options

| Short | Long | Description |
| ------- | ------ | ------------- |
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
| `-b` | `--pre-announcement TEXT` | Text to announce before main content |
| `-a` | `--post-announcement TEXT` | Text to announce after main content |
| | `--dry-run` | Print text only, don't broadcast |
| | `--offline` | Offline mode - time/date only without weather API calls |

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

```markdown
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

#### Primary: Zippopotam.us

- URL: <https://api.zippopotam.us/{country}/{postalcode}>
- Free, no API key required
- Fast and lightweight

#### Fallback: OpenStreetMap Nominatim

- URL: <https://nominatim.openstreetmap.org/search>
- Free, attribution required
- Comprehensive global coverage

### Weather Service

#### Open-Meteo

- URL: <https://api.open-meteo.com/v1/forecast>
- Free, unlimited access, no API key required
- Data source: ECMWF (European Centre for Medium-Range Weather Forecasts)

### Offline Mode

When network connectivity is unavailable, use offline mode to announce only time and date:

```bash
# Via command line
asl_weather --offline

# Via configuration
# In config.ini:
# offline = true
```

In offline mode:

- No postal code lookups are performed
- No weather data is fetched
- Only time/date announcements are made (if enabled)
- Useful for network outages or testing

### Circuit Breaker Protection

The system automatically protects against cascading failures:

- **Automatic Detection**: Circuit opens after 5 consecutive API failures
- **Self-Healing**: Automatically attempts recovery after 60 seconds
- **Transparent**: Works automatically without configuration
- **Per-Service**: Separate circuit breakers for each external API

### API Metrics

All external API calls are automatically instrumented:

- **Response Times**: Average response times per service
- **Success Rates**: Track API reliability over time
- **Debug Logging**: Enable debug logging to see metrics

Enable debug logging to view metrics:

```bash
LOG_LEVEL=DEBUG asl_weather --dry-run
```

## Caching

Location lookups use an LRU (Least Recently Used) cache:

- **Sized-Based**: Default 100 entries (configurable via `cache_size`)
- **No TTL**: Entries persist until evicted (postal codes rarely change)
- **Persistent**: Cache survives script restarts
- **LRU Eviction**: When full, least recently used entries are removed first

**Cache Locations:**

- **Root users**: `/var/cache/asl_weather_announce/location_cache.json`
- **Regular users**: `~/.cache/asl_weather_announce/location_cache.json`

Clear the cache by deleting the cache file:

```bash
# As root
rm /var/cache/asl_weather_announce/location_cache.json

# As regular user
rm ~/.cache/asl_weather_announce/location_cache.json
```

## Troubleshooting

### Permission Denied

```text
This script must be run as root or the asterisk user.
```

**Solution**: Use `sudo` or run as the `asterisk` user:

```bash
sudo asl_weather
```

### Missing Dependencies

```markdown
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

```text
Warning: Voice 'en_GB-alan-low.onnx' not found in /var/lib/piper-tts
```

**Solution**: Check available voices and update configuration:

```bash
ls /var/lib/piper-tts/
```

### Postal Code Not Found

```text
Could not find location for postal code 'XXXXX' in country 'XX'
```

**Solution**:

- Verify the postal code is valid
- Try using direct latitude/longitude coordinates instead
- Check network connectivity

## Environment Variables

| Variable | Description |
| ---------- | ------------- |
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

Peter Nearing - <me@peternearing.ca>

## Version

1.0.1 - Implemented reslience and back off's.
1.0.2 - Added pre and post announcements, and output to an audio file. Add systemd service and timer, as well as crontab examples.
