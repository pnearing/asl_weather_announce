"""
Tests for the LRU Cache module.
"""

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from asl_weather_cache import LRUCache, LocationCache


class TestLRUCache(unittest.TestCase):
    """Test cases for the LRUCache class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = Path(self.temp_dir) / "test_cache.json"
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.cache_file.exists():
            self.cache_file.unlink()
        os.rmdir(self.temp_dir)
    
    def test_basic_get_set(self):
        """Test basic get and set operations."""
        cache = LRUCache(max_size=100)
        
        # Set a value
        cache.set("key1", {"data": "value1"})
        
        # Get the value
        result = cache.get("key1")
        self.assertEqual(result, {"data": "value1"})
    
    def test_get_missing_key(self):
        """Test getting a non-existent key."""
        cache = LRUCache(max_size=100)
        
        result = cache.get("nonexistent")
        self.assertIsNone(result)
    
    def test_cache_size_limit(self):
        """Test that cache respects size limits with LRU eviction."""
        cache = LRUCache(max_size=3)
        
        # Add 3 items
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it most recently used
        cache.get("key1")
        
        # Add 4th item - should evict key2 (least recently used)
        cache.set("key4", "value4")
        
        # key1 should still exist
        self.assertEqual(cache.get("key1"), "value1")
        
        # key2 should be evicted
        self.assertIsNone(cache.get("key2"))
        
        # key3 and key4 should exist
        self.assertEqual(cache.get("key3"), "value3")
        self.assertEqual(cache.get("key4"), "value4")
    
    def test_negative_caching(self):
        """Test that None values are cached properly."""
        cache = LRUCache(max_size=100)
        
        # Set None value (represents a failed lookup)
        cache.set("key1", None)
        
        # Get should return None (from cache, not missing)
        result = cache.get("key1")
        self.assertIsNone(result)
        
        # Check that key exists in cache
        self.assertIn("key1", cache.keys())
    
    def test_persistence(self):
        """Test cache persistence to disk."""
        # Create cache and add data
        cache1 = LRUCache(max_size=100, cache_file=str(self.cache_file))
        cache1.set("key1", {"data": "value1"})
        cache1.set("key2", {"data": "value2"})
        
        # Create new cache instance with same file
        cache2 = LRUCache(max_size=100, cache_file=str(self.cache_file))
        
        # Data should be loaded from disk
        self.assertEqual(cache2.get("key1"), {"data": "value1"})
        self.assertEqual(cache2.get("key2"), {"data": "value2"})
    
    def test_delete(self):
        """Test delete operation."""
        cache = LRUCache(max_size=100)
        cache.set("key1", "value1")
        
        # Delete existing key
        result = cache.delete("key1")
        self.assertTrue(result)
        self.assertIsNone(cache.get("key1"))
        
        # Delete non-existent key
        result = cache.delete("nonexistent")
        self.assertFalse(result)
    
    def test_clear(self):
        """Test clear operation."""
        cache = LRUCache(max_size=100)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))
        self.assertEqual(cache.get_size(), 0)
    
    def test_get_stats(self):
        """Test statistics tracking."""
        cache = LRUCache(max_size=100)
        
        # Add some items
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Get some items (hits and misses)
        cache.get("key1")  # hit
        cache.get("key2")  # hit
        cache.get("key3")  # miss
        
        stats = cache.get_stats()
        
        self.assertEqual(stats["total_entries"], 2)
        self.assertEqual(stats["max_size"], 100)
        self.assertEqual(stats["hits"], 2)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_rate"], 2/3)
    
    def test_thread_safety(self):
        """Test thread-safe operations."""
        cache = LRUCache(max_size=1000)
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(100):
                    key = f"worker{worker_id}_key{i}"
                    cache.set(key, f"value{i}")
                    cache.get(key)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # No errors should have occurred
        self.assertEqual(len(errors), 0)
    
    def test_lru_ordering(self):
        """Test that LRU ordering is maintained correctly."""
        cache = LRUCache(max_size=3)
        
        # Add items
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        
        # Access 'a' to make it most recent
        cache.get("a")
        
        # Add new item - should evict 'b'
        cache.set("d", 4)
        
        self.assertIsNotNone(cache.get("a"))
        self.assertIsNone(cache.get("b"))  # evicted
        self.assertIsNotNone(cache.get("c"))
        self.assertIsNotNone(cache.get("d"))


class TestLocationCache(unittest.TestCase):
    """Test cases for the LocationCache class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = Path(self.temp_dir) / "location_cache.json"
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.cache_file.exists():
            self.cache_file.unlink()
        os.rmdir(self.temp_dir)
    
    def test_default_size(self):
        """Test that LocationCache has correct default size."""
        cache = LocationCache(cache_file=str(self.cache_file))
        self.assertEqual(cache.max_size, 100)
    
    def test_custom_size(self):
        """Test that LocationCache accepts custom size."""
        cache = LocationCache(max_size=500, cache_file=str(self.cache_file))
        self.assertEqual(cache.max_size, 500)
    
    def test_postal_code_storage(self):
        """Test storing postal code lookups."""
        cache = LocationCache(cache_file=str(self.cache_file))
        
        location_data = {
            "city": "London",
            "state_province": "Ontario",
            "country": "Canada",
            "country_code": "CA",
            "latitude": 42.9837,
            "longitude": -81.2497,
            "source": "zippopotam"
        }
        
        cache.set("N6A3K7:CA", location_data)
        
        result = cache.get("N6A3K7:CA")
        self.assertEqual(result["city"], "London")
        self.assertEqual(result["state_province"], "Ontario")
    
    def test_reverse_lookup_storage(self):
        """Test storing reverse geocoding results."""
        cache = LocationCache(cache_file=str(self.cache_file))
        
        location_data = {
            "city": "Toronto",
            "state_province": "Ontario",
            "country": "Canada",
            "country_code": "CA",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "source": "nominatim_reverse"
        }
        
        cache.set("reverse:43.653200:-79.383200", location_data)
        
        result = cache.get("reverse:43.653200:-79.383200")
        self.assertEqual(result["city"], "Toronto")


class TestCachePersistence(unittest.TestCase):
    """Test cache persistence scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_corrupt_cache_file(self):
        """Test handling of corrupt cache file."""
        cache_file = Path(self.temp_dir) / "corrupt.json"
        
        # Write invalid JSON
        cache_file.write_text("not valid json {\n")
        
        # Should not crash, just start with empty cache
        cache = LRUCache(max_size=100, cache_file=str(cache_file))
        self.assertEqual(cache.get_size(), 0)
    
    def test_nonexistent_cache_dir(self):
        """Test cache creates directories if needed."""
        cache_file = Path(self.temp_dir) / "subdir" / "nested" / "cache.json"
        
        cache = LRUCache(max_size=100, cache_file=str(cache_file))
        cache.set("key", "value")
        
        # File should be created
        self.assertTrue(cache_file.exists())


if __name__ == "__main__":
    unittest.main()
