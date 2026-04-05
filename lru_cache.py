"""
LRU Cache Module for ASL Weather Announce

This module provides a simple LRU (Least Recently Used) cache with size limits
and persistent disk storage. No TTL - entries remain until evicted by size.

Usage:
    from lru_cache import LRUCache, LocationCache
    
    # Create cache with 1000 entry limit
    cache = LRUCache(max_size=1000, cache_file="/path/to/cache.json")
    
    # Store value
    cache.set("key", value)
    
    # Retrieve value (returns None if missing)
    value = cache.get("key")
"""

__version__ = "1.0.0"
__author__ = "Peter Nearing"
__email__ = "me@peternearing.ca"

import json
import logging
import os
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LRUCache:
    """
    Thread-safe LRU cache with size limits and persistence.
    
    Features:
    - Maximum size enforced with LRU eviction
    - Persistent disk storage
    - Thread-safe operations
    - No TTL - entries remain until evicted
    
    Example:
        cache = LRUCache(max_size=1000, cache_file="/var/cache/asl_weather/my_cache.json")
        
        # Store
        cache.set("key1", {"data": "value"})
        
        # Retrieve
        data = cache.get("key1")
        
        # Get statistics
        stats = cache.get_stats()
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        cache_file: Optional[str] = None,
        logger_instance: Optional[logging.Logger] = None,
    ):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries to store
            cache_file: Path to persistent cache file (None for memory-only)
            logger_instance: Optional logger instance
        """
        self.max_size = max_size
        self.cache_file = Path(cache_file) if cache_file else None
        self.logger = logger_instance or logger
        
        # Use OrderedDict for LRU tracking (most recent at end)
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        # Load from disk if available
        if self.cache_file:
            self._load_from_disk()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            value = self._cache.pop(key)
            self._cache[key] = value
            self._hits += 1
            
            return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to store
        """
        with self._lock:
            # If key exists, remove it first (will be re-added at end)
            if key in self._cache:
                del self._cache[key]
            
            # Check if we need to evict
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            # Add to end (most recently used)
            self._cache[key] = value
            
            self._save_to_disk()
    
    def delete(self, key: str) -> bool:
        """
        Delete entry from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if entry was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._save_to_disk()
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._save_to_disk()
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # OrderedDict maintains insertion order - first item is oldest
        oldest_key = next(iter(self._cache))
        del self._cache[oldest_key]
        self._evictions += 1
        self.logger.debug(f"Evicted cache entry: {oldest_key}")
    
    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        if not self.cache_file:
            return
        
        try:
            if not self.cache_file.exists():
                return
            
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                self.logger.warning("Cache file contains invalid data, starting fresh")
                return
            
            loaded_count = 0
            
            for key, value in data.items():
                self._cache[key] = value
                loaded_count += 1
                
                # Don't exceed max size on load
                if len(self._cache) >= self.max_size:
                    break
            
            self.logger.debug(f"Loaded {loaded_count} entries from cache")
            
        except (json.JSONDecodeError, OSError) as e:
            self.logger.debug(f"Could not load cache file: {e}")
    
    def _save_to_disk(self) -> None:
        """Save cache to disk."""
        if not self.cache_file:
            return
        
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with self._lock:
                data = dict(self._cache)
            
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
        except OSError as e:
            self.logger.debug(f"Could not save cache file: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_accesses = self._hits + self._misses
            hit_rate = self._hits / total_accesses if total_accesses > 0 else 0.0
            
            return {
                "total_entries": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "evictions": self._evictions,
            }
    
    def get_size(self) -> int:
        """Get current number of entries."""
        with self._lock:
            return len(self._cache)
    
    def keys(self) -> list:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())


class LocationCache(LRUCache):
    """
    Specialized cache for location lookups with sensible defaults.
    
    Postal codes rarely change, so we use a cache with no TTL.
    Default size is suitable for most stationary nodes.
    """
    
    DEFAULT_MAX_SIZE = 100  # Reasonable default for stationary nodes
    
    def __init__(
        self,
        max_size: Optional[int] = None,
        cache_file: Optional[str] = None,
        logger_instance: Optional[logging.Logger] = None,
    ):
        """
        Initialize location cache.
        
        Args:
            max_size: Maximum cache entries (default: 100)
            cache_file: Path to cache file (auto-detected if None)
            logger_instance: Optional logger
        """
        if cache_file is None:
            cache_file = self._get_default_cache_path()
        
        super().__init__(
            max_size=max_size or self.DEFAULT_MAX_SIZE,
            cache_file=cache_file,
            logger_instance=logger_instance,
        )
    
    @staticmethod
    def _get_default_cache_path() -> str:
        """Get default cache path based on user privileges."""
        if os.geteuid() == 0:  # Running as root
            return "/var/cache/asl_weather_announce/location_cache.json"
        else:
            return str(Path.home() / ".cache" / "asl_weather_announce" / "location_cache.json")
