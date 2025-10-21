"""
Response Caching System
Cache LLM responses to save API calls and improve performance.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any


class ResponseCache:
    """Cache for LLM responses to reduce API calls"""

    def __init__(self, cache_dir: Optional[str] = None, ttl_hours: int = 24):
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files (default: ~/.lumecode/cache)
            ttl_hours: Time-to-live for cache entries in hours
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".lumecode" / "cache"

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self.stats_file = self.cache_dir / "stats.json"
        self._load_stats()

    def _load_stats(self):
        """Load cache statistics"""
        if self.stats_file.exists():
            with open(self.stats_file, "r") as f:
                self.stats = json.load(f)
        else:
            self.stats = {
                "hits": 0,
                "misses": 0,
                "saves": 0,
                "total_saved_api_calls": 0,
                "created_at": datetime.now().isoformat(),
            }

    def _save_stats(self):
        """Save cache statistics"""
        with open(self.stats_file, "w") as f:
            json.dump(self.stats, f, indent=2)

    def _get_cache_key(
        self, prompt: str, provider: str, model: str, temperature: float, max_tokens: int
    ) -> str:
        """
        Generate cache key from request parameters.

        Args:
            prompt: User prompt
            provider: LLM provider name
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens

        Returns:
            Cache key (hash)
        """
        # Create deterministic string from parameters
        cache_string = f"{provider}:{model}:{temperature}:{max_tokens}:{prompt}"

        # Hash it
        return hashlib.sha256(cache_string.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get path to cache file"""
        # Use first 2 chars as subdirectory for better file organization
        subdir = self.cache_dir / cache_key[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / f"{cache_key}.json"

    def get(
        self,
        prompt: str,
        provider: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Optional[str]:
        """
        Get cached response if available and not expired.

        Args:
            prompt: User prompt
            provider: LLM provider name
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens

        Returns:
            Cached response or None if not found/expired
        """
        cache_key = self._get_cache_key(prompt, provider, model, temperature, max_tokens)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            self.stats["misses"] += 1
            self._save_stats()
            return None

        # Load cached data
        with open(cache_path, "r") as f:
            cached_data = json.load(f)

        # Check if expired
        cached_time = datetime.fromisoformat(cached_data["timestamp"])
        expiry_time = cached_time + timedelta(hours=self.ttl_hours)

        if datetime.now() > expiry_time:
            # Expired, remove it
            cache_path.unlink()
            self.stats["misses"] += 1
            self._save_stats()
            return None

        # Cache hit!
        self.stats["hits"] += 1
        self.stats["total_saved_api_calls"] += 1
        self._save_stats()

        return cached_data["response"]

    def set(
        self,
        prompt: str,
        provider: str,
        model: str,
        response: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        """
        Cache a response.

        Args:
            prompt: User prompt
            provider: LLM provider name
            model: Model name
            response: LLM response
            temperature: Sampling temperature
            max_tokens: Max tokens
        """
        cache_key = self._get_cache_key(prompt, provider, model, temperature, max_tokens)
        cache_path = self._get_cache_path(cache_key)

        # Save to cache
        cached_data = {
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response": response,
            "timestamp": datetime.now().isoformat(),
        }

        with open(cache_path, "w") as f:
            json.dump(cached_data, f, indent=2)

        self.stats["saves"] += 1
        self._save_stats()

    def clear(self, older_than_hours: Optional[int] = None):
        """
        Clear cache.

        Args:
            older_than_hours: Only clear entries older than N hours (None = clear all)
        """
        count = 0

        for cache_file in self.cache_dir.rglob("*.json"):
            if cache_file.name == "stats.json":
                continue

            if older_than_hours:
                # Check age
                with open(cache_file, "r") as f:
                    data = json.load(f)
                cached_time = datetime.fromisoformat(data["timestamp"])
                age = datetime.now() - cached_time

                if age.total_seconds() > older_than_hours * 3600:
                    cache_file.unlink()
                    count += 1
            else:
                # Clear all
                cache_file.unlink()
                count += 1

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        # Calculate cache size
        cache_size_bytes = sum(
            f.stat().st_size for f in self.cache_dir.rglob("*.json") if f.name != "stats.json"
        )
        cache_size_mb = cache_size_bytes / (1024 * 1024)

        # Count entries
        num_entries = len(list(self.cache_dir.rglob("*.json"))) - 1  # Exclude stats.json

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "total_requests": total_requests,
            "hit_rate": f"{hit_rate:.1f}%",
            "saves": self.stats["saves"],
            "total_saved_api_calls": self.stats["total_saved_api_calls"],
            "cache_size_mb": f"{cache_size_mb:.2f}",
            "num_entries": num_entries,
            "created_at": self.stats["created_at"],
        }

    def info(self) -> str:
        """Get formatted cache information"""
        stats = self.get_stats()

        info = [
            "📊 Cache Statistics:",
            f"  Cache directory: {self.cache_dir}",
            f"  Entries: {stats['num_entries']}",
            f"  Size: {stats['cache_size_mb']} MB",
            f"  TTL: {self.ttl_hours} hours",
            "",
            "📈 Performance:",
            f"  Hits: {stats['hits']}",
            f"  Misses: {stats['misses']}",
            f"  Hit rate: {stats['hit_rate']}",
            f"  API calls saved: {stats['total_saved_api_calls']}",
            "",
            f"⏰ Created: {stats['created_at']}",
        ]

        return "\n".join(info)


# Global cache instance
_cache_instance = None


def get_cache(cache_dir: Optional[str] = None, ttl_hours: int = 24) -> ResponseCache:
    """Get global cache instance"""
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = ResponseCache(cache_dir, ttl_hours)

    return _cache_instance
