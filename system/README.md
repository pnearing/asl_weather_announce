# Systemd Timer and Service for ASL Weather Announce

This directory contains systemd unit files for running `asl_weather` automatically on a schedule.

## Files

- `asl-weather.service` - The service unit that executes the weather announcement
- `asl-weather.timer` - The timer unit that triggers the service every hour on the hour (:00)

## Installation via .deb Package

When you install the `asl-weather-announce` package, the systemd timer and service files are automatically installed to `/etc/systemd/system/`. **However, the timer is NOT enabled or started by default** — you must manually enable it when you're ready.

After installing the package:

```bash
# Reload systemd to recognize the new units
sudo systemctl daemon-reload

# Enable and start the timer (when you're ready)
sudo systemctl enable asl-weather.timer
sudo systemctl start asl-weather.timer
```

## Manual Installation

If you prefer to install the unit files manually instead of via the package:

```bash
sudo cp asl-weather.service /etc/systemd/system/
sudo cp asl-weather.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable asl-weather.timer
sudo systemctl start asl-weather.timer
```

## Verification

Check that the timer is active and scheduled correctly:

```bash
sudo systemctl status asl-weather.timer
```

View the next scheduled run times:

```bash
systemctl list-timers asl-weather.timer
```

## Configuration

Ensure your configuration file is in place at `/etc/asl_weather.conf` with your location and node settings. See the main README.md for configuration details.

## Logs

View recent logs:

```bash
sudo journalctl -u asl-weather -n 50
```

Follow logs in real-time:

```bash
sudo journalctl -u asl-weather -f
```

## Stopping/Disabling

To stop the timer:

```bash
sudo systemctl stop asl-weather.timer
```

To disable the timer from starting on boot:

```bash
sudo systemctl disable asl-weather.timer
```

## Modifying Timer Frequency

The default timer runs every hour on the hour. To change the frequency, edit the `OnCalendar` directive in `asl-weather.timer`:

```bash
sudo systemctl edit --full asl-weather.timer
```

Or edit the file directly (if manually installed):

```bash
sudo nano /etc/systemd/system/asl-weather.timer
```

Common `OnCalendar` patterns:

| Pattern | Description |
|---------|-------------|
| `*-*-* *:00:00` | Every hour on the hour (default) |
| `*-*-* *:30:00` | Every hour at :30 |
| `*-*-* 08,12,18:00:00` | At 08:00, 12:00, and 18:00 daily |
| `*-*-* 08:00:00` | Once daily at 08:00 |
| `*-*-* *:*:00` | Every minute (for testing only!) |
| `Mon *-*-* 08:00:00` | Every Monday at 08:00 |

After modifying the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl restart asl-weather.timer
```

## Command Line Options

You can pass command line options to `asl_weather` by modifying the `ExecStart` line in the service file:

```bash
sudo systemctl edit --full asl-weather.service
```

Or create a drop-in override:

```bash
sudo systemctl edit asl-weather.service
```

Then add your options to the override file:

```ini
[Service]
# First, clear the default ExecStart (required when overriding in a drop-in)
ExecStart=
# Then set the new ExecStart with your desired options
ExecStart=/usr/bin/asl_weather --log-file /var/log/asl_weather.log --say-time
```

**Why the empty `ExecStart=` line?** When using a drop-in override (via `systemctl edit`), systemd appends your new settings to the existing service definition. Since systemd doesn't allow duplicate directives, you must first clear the original `ExecStart` with an empty assignment before setting your new value. This is standard systemd behavior for overriding executable commands.

### Available Options

| Option | Description | Example |
|--------|-------------|---------|
| `--log-file PATH` | Log output to file | `--log-file /var/log/asl_weather.log` |
| `--say-time` | Announce current time | `--say-time` |
| `--say-date` | Announce current date | `--say-date` |
| `--temperature-unit C/F` | Temperature unit | `--temperature-unit F` |
| `--dry-run` | Print text only (no broadcast) | `--dry-run` |
| `--test-config` | Validate config and exit | `--test-config` |

## Advanced Usage Example

Here's an advanced setup that announces **date, time, and weather at 08:00**, and **time and weather only at all other hours**.

### Method 1: Two Separate Timer/Service Pairs

Create two service files with different options:

**Step 1:** Create `/etc/systemd/system/asl-weather-full.service`:

```ini
[Unit]
Description=ASL Weather Announce with Date/Time
After=network.target asterisk.service

[Service]
Type=oneshot
ExecStart=/usr/bin/asl_weather --say-date --say-time --log-file /var/log/asl_weather.log
StandardOutput=journal
StandardError=journal
SyslogIdentifier=asl-weather
```

**Step 2:** Create `/etc/systemd/system/asl-weather-full.timer`:

```ini
[Unit]
Description=Run full ASL Weather Announce at 08:00
Requires=asl-weather-full.service

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Step 3:** Modify the existing service for other hours (`/etc/systemd/system/asl-weather.service`):

```ini
[Unit]
Description=ASL Weather Announce Service
After=network.target asterisk.service

[Service]
Type=oneshot
ExecStart=/usr/bin/asl_weather --say-time --log-file /var/log/asl_weather.log
StandardOutput=journal
StandardError=journal
SyslogIdentifier=asl-weather
```

**Step 4:** Modify the existing timer to exclude 08:00 (`/etc/systemd/system/asl-weather.timer`):

```ini
[Unit]
Description=Run ASL Weather Announce every hour except 08:00
Requires=asl-weather.service

[Timer]
OnCalendar=*-*-* 00,01,02,03,04,05,06,07,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Step 5:** Enable and start both timers:

```bash
sudo systemctl daemon-reload
sudo systemctl enable asl-weather.timer asl-weather-full.timer
sudo systemctl start asl-weather.timer asl-weather-full.timer
```

### Method 2: Using a Wrapper Script (More Flexible)

Create a wrapper script that checks the hour and calls `asl_weather` with appropriate options:

**Step 1:** Create `/usr/local/bin/asl-weather-smart.sh`:

```bash
#!/bin/bash
# Smart ASL Weather wrapper - announces date+time at 08:00, time only at other hours

HOUR=$(date +%H)
LOG_FILE="/var/log/asl_weather.log"

if [ "$HOUR" -eq 08 ]; then
    # 08:00 - Full announcement with date, time, and weather
    /usr/bin/asl_weather --say-date --say-time --log-file "$LOG_FILE"
else
    # Other hours - Time and weather only
    /usr/bin/asl_weather --say-time --log-file "$LOG_FILE"
fi
```

**Step 2:** Make it executable:

```bash
sudo chmod +x /usr/local/bin/asl-weather-smart.sh
```

**Step 3:** Edit the service to use the wrapper:

```bash
sudo systemctl edit --full asl-weather.service
```

```ini
[Unit]
Description=ASL Weather Announce Service
After=network.target asterisk.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/asl-weather-smart.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=asl-weather
```

**Step 4:** Reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart asl-weather.timer
```

## Alternative: Cron

If you prefer cron over systemd timers, add entries to your crontab (edit with `sudo crontab -e`):

```cron
# Run ASL Weather Announce every hour on the hour
0 * * * * /usr/bin/asl_weather --log-file /var/log/asl_weather.cron.log
```

### Cron Advanced Example (08:00 full announcement, other hours time only)

```cron
# At 08:00: Full announcement with date, time, and weather
0 8 * * * /usr/bin/asl_weather --say-date --say-time --log-file /var/log/asl_weather.log

# At all other hours (00-07, 09-23): Time and weather only
0 0,1,2,3,4,5,6,7,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23 * * * /usr/bin/asl_weather --say-time --log-file /var/log/asl_weather.log
```

Or using a wrapper script with cron:

```cron
# Run smart wrapper every hour
0 * * * * /usr/local/bin/asl-weather-smart.sh
```

**Note:** The `asl_weather` script requires root or asterisk user privileges to run.
