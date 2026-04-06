# ASL Weather Announce - Makefile for Debian Packaging

PACKAGE_NAME = asl-weather-announce
VERSION = $(shell dpkg-parsechangelog -S Version 2>/dev/null || echo "1.0.0")

# Prevent recursive calls during debhelper builds
ifeq ($(DEB_BUILD_OPTIONS),)
  IS_TOP_LEVEL = yes
endif

.PHONY: all build clean install deb source release

all: deb

# Build the Debian package (only at top level)
build:
ifeq ($(IS_TOP_LEVEL),yes)
	dpkg-buildpackage -us -uc -b
else
	@echo "Skipping recursive build during debhelper"
endif

# Build Debian package (same as build)
deb:
ifeq ($(IS_TOP_LEVEL),yes)
	dpkg-buildpackage -us -uc -b
else
	@echo "Skipping recursive deb during debhelper"
endif

# Create source tarball
source:
	cd .. && tar czf "$(PACKAGE_NAME)_$(VERSION).orig.tar.gz" \
		--exclude='.git' \
		--exclude='.github' \
		--exclude='.forgejo' \
		--exclude='debian' \
		--exclude='*.pyc' \
		--exclude='__pycache__' \
		--exclude='.venv' \
		--transform "s|^asl_weather_announce|$(PACKAGE_NAME)-$(VERSION)|" \
		asl_weather_announce/

# Build source package
source-pkg:
	dpkg-buildpackage -us -uc -S

# Clean build artifacts
clean:
	dh_clean
	rm -rf debian/$(PACKAGE_NAME)
	rm -f ../$(PACKAGE_NAME)_*.deb
	rm -f ../$(PACKAGE_NAME)_*.changes
	rm -f ../$(PACKAGE_NAME)_*.buildinfo
	rm -f ../$(PACKAGE_NAME)_*.tar.gz

# Install locally (for testing)
install:
	install -D -m 755 asl_weather.py $(DESTDIR)/usr/bin/asl_weather
	install -D -m 644 config.ini.example $(DESTDIR)/etc/asl_weather.conf.example
	# Install Python modules
	install -d -m 755 $(DESTDIR)/usr/lib/python3/dist-packages/get_weather
	install -d -m 755 $(DESTDIR)/usr/lib/python3/dist-packages/get_weather/data
	install -d -m 755 $(DESTDIR)/usr/lib/python3/dist-packages/get_location
	install -d -m 755 $(DESTDIR)/usr/lib/python3/dist-packages/get_location/data
	install -m 644 get_weather/*.py $(DESTDIR)/usr/lib/python3/dist-packages/get_weather/
	install -m 644 get_weather/data/*.json $(DESTDIR)/usr/lib/python3/dist-packages/get_weather/data/
	install -m 644 get_location/*.py $(DESTDIR)/usr/lib/python3/dist-packages/get_location/
	install -m 644 get_location/data/*.json $(DESTDIR)/usr/lib/python3/dist-packages/get_location/data/
	# Install asl_weather package
	install -d -m 755 $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather
	install -m 644 asl_weather/__init__.py $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather/
	install -m 644 asl_weather/asl_weather_build_annoucement.py $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather/
	install -m 644 asl_weather/asl_weather_checks.py $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather/
	install -m 644 asl_weather/asl_weather_config.py $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather/
	install -m 644 asl_weather/asl_weather_constants.py $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather/
	install -m 644 asl_weather/asl_weather_cache.py $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather/
	install -m 644 asl_weather/asl_weather_logging.py $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather/
	install -m 644 asl_weather/asl_weather_resilience.py $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather/
	install -d -m 755 $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather/data
	install -m 644 asl_weather/data/*.json $(DESTDIR)/usr/lib/python3/dist-packages/asl_weather/data/

# Lint the package
lint:
	lintian ../$(PACKAGE_NAME)_*.deb

# Full release build (deb + source tarball)
release: deb source
	@echo "Release artifacts built:"
	@ls -la ../*.deb ../*.tar.gz 2>/dev/null || true

# Help
help:
	@echo "ASL Weather Announce - Makefile targets:"
	@echo "  make build      - Build the Debian package"
	@echo "  make deb        - Same as build"
	@echo "  make source     - Create source tarball"
	@echo "  make source-pkg - Build source package"
	@echo "  make release    - Build both deb and source tarball"
	@echo "  make lint       - Run lintian on the built package"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make install    - Install locally (for testing)"
	@echo "  make help       - Show this help"
