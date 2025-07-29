import pickle
from collections import UserList
from multiprocessing import shared_memory
from typing import Any, Generic, TypeVar, List as PyList
from .namedLock import NamedLock

T = TypeVar("T")

class RememoryList(UserList, Generic[T]):
    """
    A true shared-memory list using multiprocessing.shared_memory.
    Any Python process (spawned or launched independently) that constructs
    RememoryList("name") will attach to the same shared memory block.

    Synchronization is handled via a NamedLock (cross-process).
    """

    _value_type: Any = Any

    def __class_getitem__(cls, item):
        val_t = item

        class _TypedRememoryList(RememoryList):  # type: ignore
            _value_type = val_t

        _TypedRememoryList.__name__ = (
            f"RememoryList[{getattr(val_t, '__name__', str(val_t))}]"
        )
        return _TypedRememoryList

    def __init__(self, name: str, size: int = 65536):
        self._name = name
        self._size = size
        self._shm = None

        # Try to attach; if it doesn't exist, create it
        try:
            self._shm = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            self._shm = shared_memory.SharedMemory(name=name, create=True, size=size)
            self._write_data([])

        self._lock = NamedLock(name)

        # Initialize UserList with a snapshot
        super().__init__(self._read_data())

    # ---------------- Internal helpers ----------------

    def _read_data(self) -> PyList[Any]:
        if self._shm is None:
            return []
        raw = bytes(self._shm.buf).rstrip(b"\x00")
        if not raw:
            return []
        try:
            return pickle.loads(raw)
        except Exception:
            return []

    def _write_data(self, data: PyList[Any]):
        if self._shm is None:
            return
        encoded = pickle.dumps(data)
        if len(encoded) > self._shm.size:
            new_size = max(len(encoded), self._shm.size * 2)
            self._shm.close()
            self._shm.unlink()
            self._shm = shared_memory.SharedMemory(
                name=self._name, create=True, size=new_size
            )
        self._shm.buf[: len(encoded)] = encoded
        self._shm.buf[len(encoded) :] = b"\x00" * (self._shm.size - len(encoded))

    # ---------------- Mutating methods ----------------

    def append(self, item: T) -> None:
        with self._lock:
            data = self._read_data()
            data.append(item)
            self._write_data(data)

    def insert(self, i: int, item: T) -> None:
        with self._lock:
            data = self._read_data()
            data.insert(i, item)
            self._write_data(data)

    def __setitem__(self, index, value):  # index can be int or slice
        with self._lock:
            data = self._read_data()
            data[index] = value
            self._write_data(data)

    def __delitem__(self, index):
        with self._lock:
            data = self._read_data()
            del data[index]
            self._write_data(data)

    def __getitem__(self, index):
        with self._lock:
            data = self._read_data()
            return data[index]

    def __len__(self) -> int:
        with self._lock:
            return len(self._read_data())

    def __iter__(self):
        with self._lock:
            return iter(self._read_data())

    def __repr__(self):
        return f"<RememoryList {self._name}: {self._read_data()}>"

    def close(self):
        if self._shm is None:
            return
        self._shm.close()

    def unlink(self):
        if self._shm is None:
            return
        self._shm.unlink()
