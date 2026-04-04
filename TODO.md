# ASL Weather Announce - TODO

## GPS Integration (gpsd)

- [ ] Add support for gpsd daemon for mobile/vehicle stations
  - [ ] Create GPS lookup module with gpsd client integration
  - [ ] Add configuration options for gpsd host/port (default: localhost:2947)
  - [ ] Implement coordinate validation and error handling for GPS data
  - [ ] Add fallback logic: GPS → manual coordinates → postal code
  - [ ] Cache GPS location to reduce lookups when stationary
  - [ ] Add minimum accuracy threshold (HDOP) for valid GPS data
  - [ ] Handle GPS signal loss gracefully with last-known-location fallback

## Core Features

- [ ] Add severe weather alerts/warnings integration
- [ ] Add weather forecast support (today, tomorrow, 3-day outlook)
- [ ] Support multiple location profiles (home, travel destinations)
- [ ] Add wind speed and direction as an optional detail to weather announcements
- [ ] Add humidity and air pressure as optional details
- [ ] Add sunrise/sunset time announcements

## Voice & Audio

- [ ] Support multiple voices for different announcement types
- [ ] Add pre-announcement, post-announcement, and tone/beep options
- [ ] Add audio file output option (for manual review/testing)

## System Integration

- [ ] Add systemd service file example
- [ ] Add log rotation configuration example
- [ ] Add ASL node status check before announcement
- [ ] Add repeater COS/busy detection to avoid interrupting traffic

## Testing & Quality

- [ ] Add unit tests for location lookup
- [ ] Add unit tests for weather data parsing
- [ ] Add integration tests with mocked APIs
- [ ] Add test mode that validates config without making announcements

## Documentation

- [ ] Add troubleshooting guide for common GPS issues
- [ ] Add example configurations for different use cases
- [ ] Document API rate limits and caching behavior
- [ ] Add contributor guide and code style documentation

## Performance & Reliability

- [ ] Implement exponential backoff for failed API requests
- [ ] Add circuit breaker pattern for external services
- [ ] Add metrics/logging for API usage and response times
- [ ] Optimize cache size limits and TTL
- [ ] Add offline mode with cached data only

## Internationalization

- [ ] Add support for metric vs imperial units automatically by country
- [ ] Add localized weather descriptions for non-English TTS voices
- [ ] Add timezone auto-detection from coordinates
- [ ] Add translation support for weather descriptions
