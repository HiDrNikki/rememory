import struct
from multiprocessing import shared_memory
from .namedLock import NamedLock
from enum import Enum

class FloatTypes(Enum):
    FLOAT32 = "f"  # struct format for 32-bit float
    FLOAT64 = "d"  # struct format for 64-bit float

class RememoryFloat:
    """
    A single float value stored in shared memory, synchronized with a NamedLock.
    Uses binary encoding via struct (default: double precision).
    """

    def __init__(self, name: str, fType: FloatTypes = FloatTypes.FLOAT64):
        """
        :param name: Name of the shared memory block
        :param fmt: struct format ('f' for float32, 'd' for float64)
        """
        self._name = name
        self._fType = fType
        self._size = struct.calcsize(fType.value)
        self._shm = None

        try:
            self._shm = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            self._shm = shared_memory.SharedMemory(name=name, create=True, size=self._size)
            self._write_value(0.0)

        self._lock = NamedLock(name)

    # Internal helpers
    def _read_value(self) -> float:
        if self._shm is None:
            return 0.0
        data = self._shm.buf[: self._size]
        return struct.unpack(self._fType.value, data)[0]

    def _write_value(self, value: float):
        if self._shm is None:
            return
        packed = struct.pack(self._fType.value, value)
        self._shm.buf[: self._size] = packed

    # Public interface
    @property
    def value(self) -> float:
        with self._lock:
            return self._read_value()

    @value.setter
    def value(self, new_value: float):
        with self._lock:
            self._write_value(new_value)

    def set(self, new_value: float):
        self.value = new_value

    def get(self) -> float:
        return self.value

    def __float__(self) -> float:
        return self.value

    def __repr__(self):
        return f"<RememoryFloat {self._name}: {self._read_value()}>"

    def close(self):
        if self._shm is not None:
            self._shm.close()

    def unlink(self):
        if self._shm is not None:
            self._shm.unlink()
