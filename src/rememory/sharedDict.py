import pickle
from collections import UserDict
from multiprocessing import shared_memory
from typing import Any, Generic, TypeVar, Dict as PyDict
from .namedLock import NamedLock

KT = TypeVar("KT")
VT = TypeVar("VT")

class RememoryDict(UserDict, Generic[KT, VT]):
    """
    A true shared-memory dictionary using multiprocessing.shared_memory.
    Any Python process (spawned or launched independently) that constructs
    RememoryDict("name") will attach to the same shared memory block.

    Synchronization is handled via an OS-level Semaphore (no Manager required).
    """
    _key_type: Any = Any
    _value_type: Any = Any

    def __class_getitem__(cls, item):
        if not isinstance(item, tuple):
            item = (item, Any)
        key_t, val_t = item

        class _TypedRememoryDict(RememoryDict):  # type: ignore
            _key_type = key_t
            _value_type = val_t

        _TypedRememoryDict.__name__ = (
            f"RememoryDict[{getattr(key_t, '__name__', str(key_t))}, "
            f"{getattr(val_t, '__name__', str(val_t))}]"
        )
        return _TypedRememoryDict

    def __init__(self, name: str, size: int = 65536):
        self._name = name
        self._size = size
        self._shm = None

        # Try to attach; if it doesn't exist, create it
        try:
            self._shm = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            self._shm = shared_memory.SharedMemory(name=name, create=True, size=size)
            self._write_data({})

        self._lock = NamedLock(name)

        super().__init__(self._read_data())

    def _read_data(self) -> PyDict[Any, Any]:
        """Read pickled data from shared memory into a dict."""
        if self._shm is None:
            return {}
        raw = bytes(self._shm.buf).rstrip(b"\x00")
        if not raw:
            return {}
        try:
            return pickle.loads(raw)
        except Exception:
            return {}

    def _write_data(self, data: PyDict[Any, Any]):
        """Write dict as pickled bytes into shared memory."""
        if self._shm is None:
            return
        encoded = pickle.dumps(data)
        if len(encoded) > self._shm.size:
            # Resize: create a new shared memory block (bigger)
            new_size = max(len(encoded), self._shm.size * 2)
            self._shm.close()
            self._shm.unlink()
            self._shm = shared_memory.SharedMemory(name=self._name, create=True, size=new_size)
        # Clear buffer then write
        self._shm.buf[:len(encoded)] = encoded
        self._shm.buf[len(encoded):] = b"\x00" * (self._shm.size - len(encoded))

    def __getitem__(self, key: KT) -> VT:
        with self._lock:
            data = self._read_data()
            return data[key]

    def __setitem__(self, key: KT, value: VT):
        with self._lock:
            data = self._read_data()
            data[key] = value
            self._write_data(data)

    def __delitem__(self, key: KT):
        with self._lock:
            data = self._read_data()
            del data[key]
            self._write_data(data)

    def __iter__(self):
        with self._lock:
            return iter(self._read_data())

    def __len__(self) -> int:
        with self._lock:
            return len(self._read_data())

    def items(self):
        with self._lock:
            return self._read_data().items()

    def __repr__(self):
        return f"<RememoryDict {self._name}: {self._read_data()}>"
    
    def __contains__(self, key: int) -> bool:  # type: ignore[override]
        with self._lock:
            data = self._read_data()
        return key in data
    
    def close(self):
        if self._shm is None:
            return
        self._shm.close()

    def unlink(self):
        if self._shm is None:
            return
        self._shm.unlink()