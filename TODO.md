# ASL Weather Announce - TODO

## Core Features

- [ ] Add severe weather alerts/warnings integration
- [ ] Add weather forecast support (today, tomorrow, 3-day outlook)
- [ ] Add wind speed and direction as an optional detail to weather announcements
- [ ] Add humidity and air pressure as optional details
- [ ] Add sunrise/sunset time announcements
- [ ] Add option to not announce the weather

## GPS Integration (gpsd)

- [ ] Add support for gpsd daemon for mobile/vehicle stations
  - [ ] Create GPS lookup module with gpsd client integration
  - [ ] Add configuration options for gpsd host/port (default: localhost:2947)
  - [ ] Implement coordinate validation and error handling for GPS data
  - [ ] Add fallback logic: GPS → manual coordinates → postal code
  - [ ] Cache GPS location to reduce lookups when stationary
  - [ ] Add minimum accuracy threshold (HDOP) for valid GPS data
  - [ ] Handle GPS signal loss gracefully with last-known-location fallback

## Voice & Audio

- [x] Add pre-announcement and post-announcement options
- [x] Add audio file output option (for manual review/testing)

## System Integration

- [x] Add systemd service / timer file example, or cron job example
- [x] Add log rotation configuration example
- [ ] Add ASL node status check before announcement
- [ ] Add repeater COS/busy detection to avoid interrupting traffic

## Testing & Quality

- [x] Add unit tests for location lookup
- [x] Add unit tests for weather data parsing
- [x] Add integration tests with mocked APIs
- [x] Add test mode that validates config without making announcements (--test-config flag)

## Documentation

- [ ] Add troubleshooting guide for common GPS issues
- [x] Add example configurations for different use cases
- [x] Document API rate limits and caching behavior

## Performance & Reliability

- [x] Implement exponential backoff for failed API requests
- [x] Add circuit breaker pattern for external services
- [x] Add metrics/logging for API usage and response times
- [x] Optimize cache size limits and TTL
- [x] Add offline mode, where only the time and date can be announced

## Internationalization

- [ ] Add support for metric vs imperial units automatically by country
- [ ] Add localized weather descriptions for non-English TTS voices
- [ ] Add timezone auto-detection from coordinates
- [ ] Add translation support for weather descriptions
