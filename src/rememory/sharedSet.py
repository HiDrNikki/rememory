import pickle
from collections import UserList
from multiprocessing import shared_memory
from typing import Any, Generic, TypeVar, Set as PySet, Iterator
from .namedLock import NamedLock

T = TypeVar("T")

class RememorySet(Generic[T]):
    """
    A true shared-memory set using multiprocessing.shared_memory.
    Any Python process (spawned or launched independently) that constructs
    RememorySet("name") will attach to the same shared memory block.

    Synchronization is handled via a NamedLock (cross-process).
    """

    _value_type: Any = Any

    def __class_getitem__(cls, item):
        val_t = item

        class _TypedRememorySet(RememorySet):  # type: ignore
            _value_type = val_t

        _TypedRememorySet.__name__ = (
            f"RememorySet[{getattr(val_t, '__name__', str(val_t))}]"
        )
        return _TypedRememorySet

    def __init__(self, name: str, size: int = 65536):
        self._name = name
        self._size = size
        self._shm = None

        # Try to attach; if it doesn't exist, create it
        try:
            self._shm = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            self._shm = shared_memory.SharedMemory(name=name, create=True, size=size)
            self._writeData(set())

        self._lock = NamedLock(name)

    # ---------------- Internal helpers ----------------

    def _readData(self) -> PySet[Any]:
        if self._shm is None:
            return set()
        raw = bytes(self._shm.buf).rstrip(b"\x00")
        if not raw:
            return set()
        try:
            return pickle.loads(raw)
        except Exception:
            return set()

    def _writeData(self, data: PySet[Any]):
        if self._shm is None:
            return
        encoded = pickle.dumps(data)
        if len(encoded) > self._shm.size:
            newSize = max(len(encoded), self._shm.size * 2)
            self._shm.close()
            self._shm.unlink()
            self._shm = shared_memory.SharedMemory(
                name=self._name, create=True, size=newSize
            )
        self._shm.buf[: len(encoded)] = encoded
        self._shm.buf[len(encoded) :] = b"\x00" * (self._shm.size - len(encoded))

    # ---------------- Set methods ----------------

    def add(self, item: T) -> None:
        """Add an element to the set."""
        with self._lock:
            data = self._readData()
            data.add(item)
            self._writeData(data)

    def remove(self, item: T) -> None:
        """Remove an element from the set. Raises KeyError if not found."""
        with self._lock:
            data = self._readData()
            data.remove(item)
            self._writeData(data)

    def discard(self, item: T) -> None:
        """Remove an element from the set if present."""
        with self._lock:
            data = self._readData()
            data.discard(item)
            self._writeData(data)

    def pop(self) -> T:
        """Remove and return an arbitrary element from the set."""
        with self._lock:
            data = self._readData()
            if not data:
                raise KeyError("pop from empty set")
            result = data.pop()
            self._writeData(data)
            return result

    def clear(self) -> None:
        """Remove all elements from the set."""
        with self._lock:
            self._writeData(set())

    def update(self, *others) -> None:
        """Update the set, adding elements from all others."""
        with self._lock:
            data = self._readData()
            data.update(*others)
            self._writeData(data)

    def intersectionUpdate(self, *others) -> None:
        """Update the set, keeping only elements found in it and all others."""
        with self._lock:
            data = self._readData()
            data.intersection_update(*others)
            self._writeData(data)

    def differenceUpdate(self, *others) -> None:
        """Update the set, removing elements found in others."""
        with self._lock:
            data = self._readData()
            data.difference_update(*others)
            self._writeData(data)

    def symmetricDifferenceUpdate(self, other) -> None:
        """Update the set, keeping only elements found in either set, but not in both."""
        with self._lock:
            data = self._readData()
            data.symmetric_difference_update(other)
            self._writeData(data)

    # ---------------- Read-only methods ----------------

    def __contains__(self, item: T) -> bool:
        with self._lock:
            data = self._readData()
            return item in data

    def __len__(self) -> int:
        with self._lock:
            return len(self._readData())

    def __iter__(self) -> Iterator[T]:
        with self._lock:
            return iter(self._readData())

    def copy(self) -> PySet[T]:
        """Return a shallow copy of the set."""
        with self._lock:
            return self._readData().copy()

    def isDisjoint(self, other) -> bool:
        """Return True if the set has no elements in common with other."""
        with self._lock:
            data = self._readData()
            return data.isdisjoint(other)

    def isSubset(self, other) -> bool:
        """Test whether every element in the set is in other."""
        with self._lock:
            data = self._readData()
            return data.issubset(other)

    def isSuperset(self, other) -> bool:
        """Test whether every element in other is in the set."""
        with self._lock:
            data = self._readData()
            return data.issuperset(other)

    def union(self, *others) -> PySet[T]:
        """Return the union of sets as a new set."""
        with self._lock:
            data = self._readData()
            return data.union(*others)

    def intersection(self, *others) -> PySet[T]:
        """Return the intersection of sets as a new set."""
        with self._lock:
            data = self._readData()
            return data.intersection(*others)

    def difference(self, *others) -> PySet[T]:
        """Return the difference of sets as a new set."""
        with self._lock:
            data = self._readData()
            return data.difference(*others)

    def symmetricDifference(self, other) -> PySet[T]:
        """Return the symmetric difference of sets as a new set."""
        with self._lock:
            data = self._readData()
            return data.symmetric_difference(other)

    # ---------------- Operators ----------------

    def __eq__(self, other) -> bool:
        if not isinstance(other, (set, RememorySet)):
            return False
        with self._lock:
            data = self._readData()
            if isinstance(other, RememorySet):
                with other._lock:
                    otherData = other._readData()
                    return data == otherData
            return data == other

    def __le__(self, other) -> bool:
        """Test whether every element in the set is in other (subset test)."""
        return self.isSubset(other)

    def __lt__(self, other) -> bool:
        """Test whether the set is a proper subset of other."""
        return self <= other and self != other

    def __ge__(self, other) -> bool:
        """Test whether every element in other is in the set (superset test)."""
        return self.isSuperset(other)

    def __gt__(self, other) -> bool:
        """Test whether the set is a proper superset of other."""
        return self >= other and self != other

    def __or__(self, other) -> PySet[T]:
        """Return the union of sets."""
        return self.union(other)

    def __and__(self, other) -> PySet[T]:
        """Return the intersection of sets."""
        return self.intersection(other)

    def __sub__(self, other) -> PySet[T]:
        """Return the difference of sets."""
        return self.difference(other)

    def __xor__(self, other) -> PySet[T]:
        """Return the symmetric difference of sets."""
        return self.symmetricDifference(other)

    def __repr__(self):
        return f"<RememorySet {self._name}: {self._readData()}>"

    def close(self):
        if self._shm is None:
            return
        self._shm.close()

    def unlink(self):
        if self._shm is None:
            return
        self._shm.unlink()
