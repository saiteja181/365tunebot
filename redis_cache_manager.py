#!/usr/bin/env python3
"""
Redis Cache Manager with fallback to in-memory caching
Provides persistent caching for conversation memory, query results, and dashboard data
"""

import json
import pickle
import time
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import hashlib

# Try to import Redis, fall back to in-memory if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    print("Warning: redis-py not installed. Using in-memory cache fallback.")
    print("Install with: pip install redis")
    REDIS_AVAILABLE = False


class RedisCacheManager:
    """
    Advanced caching system with Redis backend and in-memory fallback
    Supports conversation memory, query results, and dashboard data caching
    """

    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0, redis_password=None):
        """Initialize cache manager with Redis or fallback"""
        self.redis_client = None
        self.use_redis = False
        self.memory_cache = {}  # Fallback in-memory cache
        self.cache_timestamps = {}  # Track cache entry timestamps

        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=False,  # We'll handle encoding ourselves
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                self.redis_client.ping()
                self.use_redis = True
                print(f"[OK] Redis cache connected: {redis_host}:{redis_port}")
            except Exception as e:
                print(f"[WARN] Redis connection failed: {e}")
                print("[WARN] Falling back to in-memory cache")
                self.redis_client = None
                self.use_redis = False
        else:
            print("[WARN] Using in-memory cache (data will be lost on restart)")

    def _generate_cache_key(self, prefix: str, identifier: str) -> str:
        """Generate a consistent cache key"""
        return f"{prefix}:{identifier}"

    def _hash_query(self, query: str, tenant_code: str = "") -> str:
        """Generate hash for query caching"""
        combined = f"{query}|{tenant_code}".lower().strip()
        return hashlib.md5(combined.encode()).hexdigest()

    # ============================================================================
    # CONVERSATION MEMORY CACHING
    # ============================================================================

    def store_conversation_memory(self, session_id: str, user_message: str, bot_response: str,
                                  ttl: int = 86400) -> bool:
        """
        Store conversation exchange in cache
        TTL: 86400 seconds = 24 hours
        """
        try:
            cache_key = self._generate_cache_key("conversation", session_id)

            # Get existing conversation
            existing = self.get_conversation_memory(session_id) or []

            # Add new entry
            entry = {
                "user_message": user_message,
                "bot_response": bot_response,
                "timestamp": datetime.now().isoformat()
            }
            existing.append(entry)

            # Keep only last 5 exchanges
            if len(existing) > 5:
                existing = existing[-5:]

            if self.use_redis:
                # Store in Redis with TTL
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    pickle.dumps(existing)
                )
            else:
                # Store in memory
                self.memory_cache[cache_key] = existing
                self.cache_timestamps[cache_key] = time.time() + ttl

            return True
        except Exception as e:
            print(f"Error storing conversation memory: {e}")
            return False

    def get_conversation_memory(self, session_id: str) -> Optional[List[Dict]]:
        """Retrieve conversation memory for a session"""
        try:
            cache_key = self._generate_cache_key("conversation", session_id)

            if self.use_redis:
                data = self.redis_client.get(cache_key)
                if data:
                    return pickle.loads(data)
            else:
                # Check if memory cache entry is still valid
                if cache_key in self.memory_cache:
                    if cache_key in self.cache_timestamps:
                        if time.time() < self.cache_timestamps[cache_key]:
                            return self.memory_cache[cache_key]
                        else:
                            # Expired, remove it
                            del self.memory_cache[cache_key]
                            del self.cache_timestamps[cache_key]

            return None
        except Exception as e:
            print(f"Error retrieving conversation memory: {e}")
            return None

    def clear_conversation_memory(self, session_id: str) -> bool:
        """Clear conversation memory for a session"""
        try:
            cache_key = self._generate_cache_key("conversation", session_id)

            if self.use_redis:
                self.redis_client.delete(cache_key)
            else:
                if cache_key in self.memory_cache:
                    del self.memory_cache[cache_key]
                if cache_key in self.cache_timestamps:
                    del self.cache_timestamps[cache_key]

            return True
        except Exception as e:
            print(f"Error clearing conversation memory: {e}")
            return False

    # ============================================================================
    # QUERY RESULT CACHING
    # ============================================================================

    def store_query_result(self, query: str, tenant_code: str, results: Any,
                          sql_query: str = "", ttl: int = 300) -> bool:
        """
        Cache query results for 5 minutes (300 seconds)
        Reduces database load for repeated queries
        """
        try:
            query_hash = self._hash_query(query, tenant_code)
            cache_key = self._generate_cache_key("query_result", query_hash)

            cache_data = {
                "query": query,
                "tenant_code": tenant_code,
                "results": results,
                "sql_query": sql_query,
                "cached_at": datetime.now().isoformat(),
                "result_count": len(results) if results else 0
            }

            if self.use_redis:
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    pickle.dumps(cache_data)
                )
            else:
                self.memory_cache[cache_key] = cache_data
                self.cache_timestamps[cache_key] = time.time() + ttl

            return True
        except Exception as e:
            print(f"Error storing query result: {e}")
            return False

    def get_query_result(self, query: str, tenant_code: str) -> Optional[Dict]:
        """Retrieve cached query result"""
        try:
            query_hash = self._hash_query(query, tenant_code)
            cache_key = self._generate_cache_key("query_result", query_hash)

            if self.use_redis:
                data = self.redis_client.get(cache_key)
                if data:
                    cached = pickle.loads(data)
                    print(f"[OK] Cache HIT: Query result (cached at {cached['cached_at']})")
                    return cached
            else:
                if cache_key in self.memory_cache:
                    if cache_key in self.cache_timestamps:
                        if time.time() < self.cache_timestamps[cache_key]:
                            cached = self.memory_cache[cache_key]
                            print(f"[OK] Cache HIT: Query result (in-memory)")
                            return cached
                        else:
                            del self.memory_cache[cache_key]
                            del self.cache_timestamps[cache_key]

            print(f"[MISS] Cache MISS: Query will execute")
            return None
        except Exception as e:
            print(f"Error retrieving query result: {e}")
            return None

    # ============================================================================
    # DASHBOARD DATA CACHING
    # ============================================================================

    def store_dashboard_data(self, tenant_code: str, data: Dict, ttl: int = 300) -> bool:
        """
        Cache dashboard data for 5 minutes
        Improves dashboard load performance
        """
        try:
            cache_key = self._generate_cache_key("dashboard", tenant_code)

            cache_data = {
                "data": data,
                "cached_at": datetime.now().isoformat()
            }

            if self.use_redis:
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    pickle.dumps(cache_data)
                )
            else:
                self.memory_cache[cache_key] = cache_data
                self.cache_timestamps[cache_key] = time.time() + ttl

            return True
        except Exception as e:
            print(f"Error storing dashboard data: {e}")
            return False

    def get_dashboard_data(self, tenant_code: str) -> Optional[Dict]:
        """Retrieve cached dashboard data"""
        try:
            cache_key = self._generate_cache_key("dashboard", tenant_code)

            if self.use_redis:
                data = self.redis_client.get(cache_key)
                if data:
                    cached = pickle.loads(data)
                    print(f"[OK] Dashboard cache HIT (cached at {cached['cached_at']})")
                    return cached['data']
            else:
                if cache_key in self.memory_cache:
                    if cache_key in self.cache_timestamps:
                        if time.time() < self.cache_timestamps[cache_key]:
                            cached = self.memory_cache[cache_key]
                            print(f"[OK] Dashboard cache HIT (in-memory)")
                            return cached['data']
                        else:
                            del self.memory_cache[cache_key]
                            del self.cache_timestamps[cache_key]

            print(f"[MISS] Dashboard cache MISS")
            return None
        except Exception as e:
            print(f"Error retrieving dashboard data: {e}")
            return None

    # ============================================================================
    # SESSION MANAGEMENT
    # ============================================================================

    def store_session_data(self, session_id: str, data: Dict, ttl: int = 3600) -> bool:
        """Store session-specific data (1 hour TTL)"""
        try:
            cache_key = self._generate_cache_key("session", session_id)

            if self.use_redis:
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    pickle.dumps(data)
                )
            else:
                self.memory_cache[cache_key] = data
                self.cache_timestamps[cache_key] = time.time() + ttl

            return True
        except Exception as e:
            print(f"Error storing session data: {e}")
            return False

    def get_session_data(self, session_id: str) -> Optional[Dict]:
        """Retrieve session data"""
        try:
            cache_key = self._generate_cache_key("session", session_id)

            if self.use_redis:
                data = self.redis_client.get(cache_key)
                if data:
                    return pickle.loads(data)
            else:
                if cache_key in self.memory_cache:
                    if cache_key in self.cache_timestamps:
                        if time.time() < self.cache_timestamps[cache_key]:
                            return self.memory_cache[cache_key]
                        else:
                            del self.memory_cache[cache_key]
                            del self.cache_timestamps[cache_key]

            return None
        except Exception as e:
            print(f"Error retrieving session data: {e}")
            return None

    # ============================================================================
    # CACHE STATISTICS & MANAGEMENT
    # ============================================================================

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        try:
            if self.use_redis:
                info = self.redis_client.info('stats')
                return {
                    "cache_type": "Redis",
                    "connected": True,
                    "total_keys": self.redis_client.dbsize(),
                    "hits": info.get('keyspace_hits', 0),
                    "misses": info.get('keyspace_misses', 0),
                    "hit_rate": self._calculate_hit_rate(
                        info.get('keyspace_hits', 0),
                        info.get('keyspace_misses', 0)
                    )
                }
            else:
                # Clean up expired entries first
                self._cleanup_expired_entries()
                return {
                    "cache_type": "In-Memory",
                    "connected": True,
                    "total_keys": len(self.memory_cache),
                    "note": "Statistics limited in memory mode"
                }
        except Exception as e:
            return {
                "cache_type": "Unknown",
                "connected": False,
                "error": str(e)
            }

    def _calculate_hit_rate(self, hits: int, misses: int) -> str:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        if total == 0:
            return "0%"
        return f"{(hits / total * 100):.2f}%"

    def _cleanup_expired_entries(self):
        """Clean up expired entries in memory cache"""
        current_time = time.time()
        expired_keys = [
            key for key, expiry in self.cache_timestamps.items()
            if current_time >= expiry
        ]

        for key in expired_keys:
            if key in self.memory_cache:
                del self.memory_cache[key]
            if key in self.cache_timestamps:
                del self.cache_timestamps[key]

    def clear_all_cache(self) -> bool:
        """Clear all cache entries (use with caution!)"""
        try:
            if self.use_redis:
                self.redis_client.flushdb()
            else:
                self.memory_cache.clear()
                self.cache_timestamps.clear()

            print("[OK] All cache cleared")
            return True
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return False

    def clear_tenant_cache(self, tenant_code: str) -> bool:
        """Clear all cache entries for a specific tenant"""
        try:
            if self.use_redis:
                # Find all keys for this tenant
                patterns = [
                    f"dashboard:{tenant_code}",
                    f"query_result:*{tenant_code}*"
                ]

                deleted = 0
                for pattern in patterns:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        deleted += self.redis_client.delete(*keys)

                print(f"[OK] Cleared {deleted} cache entries for tenant {tenant_code}")
            else:
                # Clear from memory cache
                keys_to_delete = [
                    key for key in self.memory_cache.keys()
                    if tenant_code in key
                ]

                for key in keys_to_delete:
                    if key in self.memory_cache:
                        del self.memory_cache[key]
                    if key in self.cache_timestamps:
                        del self.cache_timestamps[key]

                print(f"[OK] Cleared {len(keys_to_delete)} cache entries for tenant {tenant_code}")

            return True
        except Exception as e:
            print(f"Error clearing tenant cache: {e}")
            return False


# Global cache instance
_cache_instance = None

def get_cache_manager() -> RedisCacheManager:
    """Get or create global cache manager instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCacheManager()
    return _cache_instance


if __name__ == "__main__":
    # Test the cache manager
    print("Testing Redis Cache Manager...")
    print("=" * 60)

    cache = get_cache_manager()

    # Test conversation memory
    print("\n1. Testing conversation memory...")
    cache.store_conversation_memory("test_session", "Hello", "Hi there!")
    cache.store_conversation_memory("test_session", "How are you?", "I'm doing great!")
    memory = cache.get_conversation_memory("test_session")
    print(f"Retrieved {len(memory)} conversation entries")

    # Test query result caching
    print("\n2. Testing query result caching...")
    cache.store_query_result("show users", "tenant123", [{"id": 1, "name": "John"}])
    result = cache.get_query_result("show users", "tenant123")
    if result:
        print(f"Cached query result: {result['result_count']} rows")

    # Test dashboard caching
    print("\n3. Testing dashboard caching...")
    cache.store_dashboard_data("tenant123", {"total_users": 100, "active": 80})
    dashboard = cache.get_dashboard_data("tenant123")
    if dashboard:
        print(f"Cached dashboard: {dashboard}")

    # Show stats
    print("\n4. Cache statistics:")
    stats = cache.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n[OK] Cache manager test complete!")
