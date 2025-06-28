import asyncio

class GlobalCache:
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()
    
    def _serialize(self, obj):
        # Handles Discord Embed and other non-serializable objects
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif "Embed" in type(obj).__name__:
            return {
                "title": getattr(obj, "title", None),
                "description": getattr(obj, "description", None),
                "fields": getattr(obj, "fields", None),
            }
        elif isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize(i) for i in obj]
        else:
            return obj

    async def get_all_serialized(self):
        async with self._lock:
            return self._serialize(self._cache)

    async def set(self, key, value):
        async with self._lock:
            self._cache[key] = value

    async def get(self, key, default=None):
        async with self._lock:
            return self._cache.get(key, default)
    
    

    async def delete(self, key):
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

global_cache = GlobalCache()
