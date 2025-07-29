from multiprocessing import shared_memory
from enum import Enum
from typing import Any, Generic, TypeVar
from .namedLock import NamedLock
import pickle
BytesType = bytes
T = TypeVar("T")

class BlockSize(Enum):
    s64 = 64
    s128 = 128
    s256 = 256
    s512 = 512
    s1024 = 1024
    s2048 = 2048
    s4096 = 4096
    s8192 = 8192
    s16384 = 16384
    s32768 = 32768

class RememoryBlock(Generic[T]):
    """Generic fixed-size shared memory block."""

    _value_type: Any = Any

    def __class_getitem__(cls, item):
        val_t = item

        class _TypedRememoryBlock(RememoryBlock):  # type: ignore
            _value_type = val_t

        _TypedRememoryBlock.__name__ = (
            f"RememoryBlock[{getattr(val_t, '__name__', str(val_t))}]"
        )
        return _TypedRememoryBlock

    def __init__(self, name: str, size: int | BlockSize):
        self._name = name
        self._size = size.value if isinstance(size, BlockSize) else size
        self._shm = None

        try:
            self._shm = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            self._shm = shared_memory.SharedMemory(name=name, create=True, size=self._size)
            self._write_bytes(b"\x00" * self._size)

        self._lock = NamedLock(name)

    def _read_bytes(self) -> BytesType:
        if self._shm is None:
            return b""
        return bytes(self._shm.buf[: self._size])

    def _write_bytes(self, data: BytesType):
        if self._shm is None:
            return
        if len(data) > self._size:
            new_size = max(len(data), self._size * 2)
            self._shm.close()
            self._shm.unlink()
            self._shm = shared_memory.SharedMemory(
                name=self._name, create=True, size=new_size
            )
            self._size = new_size
        self._shm.buf[: len(data)] = data
        self._shm.buf[len(data) : self._size] = b"\x00" * (self._size - len(data))

    # ---- Generic value helpers ----
    def _serialize_value(self, value: T) -> BytesType:
        return pickle.dumps(value)

    def _deserialize_value(self, data: BytesType) -> T:
        if not data:
            return None  # type: ignore
        return pickle.loads(data)

    def _read_value(self) -> T:
        raw = self._read_bytes().rstrip(b"\x00")
        return self._deserialize_value(raw)

    def _write_value(self, value: T):
        data = self._serialize_value(value)
        self._write_bytes(data)

    @property
    def bytes(self) -> BytesType:
        with self._lock:
            return self._read_bytes()

    @bytes.setter
    def bytes(self, data: BytesType):
        with self._lock:
            self._write_bytes(data)

    # Typed value API
    @property
    def value(self) -> T:
        with self._lock:
            return self._read_value()

    @value.setter
    def value(self, new_value: T):
        with self._lock:
            self._write_value(new_value)

    def close(self):
        if self._shm is not None:
            self._shm.close()

    def unlink(self):
        if self._shm is not None:
            self._shm.unlink()

    # Convenience methods
    def set(self, new_value: T):
        self.value = new_value

    def get(self) -> T:
        return self.value

    def __repr__(self):
        return f"<RememoryBlock {self._name}: {self._read_value()!r}>"