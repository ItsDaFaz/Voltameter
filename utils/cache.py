import asyncio

class GlobalCache:
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()

    async def set(self, key, value):
        async with self._lock:
            self._cache[key] = value

    async def get(self, key, default=None):
        async with self._lock:
            return self._cache.get(key, default)
    
    async def get_all(self):
        async with self._lock:
            return self._cache.copy()

    async def delete(self, key):
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

global_cache = GlobalCache()
