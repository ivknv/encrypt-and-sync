# -*- coding: utf-8 -*-

__all__ = ["LRUCache"]

def args_to_key(*args, **kwargs):
    return (args, tuple(kwargs.items()))

class LRUCache(object):
    def __init__(self, max_size=None):
        self._cache = {}
        self.max_size = max_size

    def __setitem__(self, key, value):
        try:
            stored = self._cache[key]
        except KeyError:
            stored = [value, 0]

        if self.max_size is not None and len(self._cache) >= self.max_size:
            max_age = None
            key_to_pop = None

            for k, v in self._cache.items():
                if max_age is None or v[1] > max_age:
                    max_age = v[1]
                    key_to_pop = k

            self._cache.pop(key_to_pop, None)

        self._cache[key] = stored

    def __getitem__(self, key):
        stored = self._cache[key]
        
        stored[1] += 1

        return stored[0]

    def __iter__(self):
        return iter(self.keys())

    def __contains__(self, key):
        return key in self._cache

    def __delitem__(self, key):
        del self._cache[key]

    def __len__(self):
        return len(self._cache)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, default=None):
        return self._cache.pop(key, (default,))[0]

    def setdefault(self, key, value):
        try:
            return self[key]
        except KeyError:
            self[key] = value

            return value

    def clear(self):
        self._cache.clear()

    def keys(self):
        return self._cache.keys()

    def values(self):
        return tuple(v for v, _ in self._cache.values())

    def items(self):
        return tuple((k, v[0]) for k, v in self._cache.items())

    def update(self, *other, **kw_other):
        if other:
            other = other[0]
        elif kw_other:
            other = kw_other
        else:
            return

        for k, v in other.items():
            self[k] = v

    @staticmethod
    def decorate(max_size=None):
        def decorator(f):
            cache = LRUCache(max_size)

            def decorated(*args, **kwargs):
                key = args_to_key(*args, **kwargs)

                try:
                    return cache[key]
                except KeyError:
                    value = f(*args, **kwargs)
                    cache[key] = value

                return value

            decorated.cache = cache
            decorated.__wrapped__ = f

            return decorated

        return decorator
