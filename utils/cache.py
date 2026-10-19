"""Yengil kesh primitivlari — tashqi bog'liqliksiz, O(1) amallar.

Bot trafigini tejashning asosiy vositasi: bir marta olingan ma'lumot
(kanallar, adminlar, obuna holati, kontent) xotirada saqlanadi va
o'zgarganda darhol bekor qilinadi.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Hashable, Iterator


class TTLCache:
    """Vaqt bo'yicha eskiradigan kesh (lazy purge — fon vazifasi kerak emas)."""

    __slots__ = ("_data", "_ttl", "_maxsize")

    def __init__(self, ttl: float, maxsize: int = 100_000) -> None:
        self._data: dict[Hashable, tuple[float, Any]] = {}
        self._ttl = ttl
        self._maxsize = maxsize

    def get(self, key: Hashable, default: Any = None) -> Any:
        hit = self._data.get(key)
        if hit is None:
            return default
        expires, value = hit
        if expires < time.monotonic():
            self._data.pop(key, None)
            return default
        return value

    def set(self, key: Hashable, value: Any, ttl: float | None = None) -> None:
        if len(self._data) >= self._maxsize:
            self.purge()
            if len(self._data) >= self._maxsize:
                # Eng eski yozuvlarning choragini olib tashlaymiz.
                for stale in sorted(self._data, key=lambda k: self._data[k][0])[
                    : self._maxsize // 4
                ]:
                    self._data.pop(stale, None)
        self._data[key] = (time.monotonic() + (self._ttl if ttl is None else ttl), value)

    def pop(self, key: Hashable) -> None:
        self._data.pop(key, None)

    def purge(self) -> int:
        now = time.monotonic()
        stale = [k for k, (exp, _) in self._data.items() if exp < now]
        for key in stale:
            del self._data[key]
        return len(stale)

    def clear(self) -> None:
        self._data.clear()

    def __contains__(self, key: Hashable) -> bool:
        return self.get(key, _MISS) is not _MISS

    def __len__(self) -> int:
        return len(self._data)


class LRUCache:
    """Sig'imi cheklangan LRU kesh — issiq kontent uchun."""

    __slots__ = ("_data", "_maxsize")

    def __init__(self, maxsize: int = 512) -> None:
        self._data: OrderedDict[Hashable, Any] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: Hashable, default: Any = None) -> Any:
        if key not in self._data:
            return default
        self._data.move_to_end(key)
        return self._data[key]

    def set(self, key: Hashable, value: Any) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def pop(self, key: Hashable) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    def __contains__(self, key: Hashable) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self._data)


_MISS = object()
