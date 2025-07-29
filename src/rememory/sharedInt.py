import struct
from multiprocessing import shared_memory
from .namedLock import NamedLock
from enum import Enum

class IntTypes(Enum):
    INT8 = "b"    # signed char (1 byte)
    UINT8 = "B"   # unsigned char (1 byte)
    INT16 = "h"   # short (2 bytes)
    UINT16 = "H"  # unsigned short (2 bytes)
    INT32 = "i"   # signed int (4 bytes)
    UINT32 = "I"  # unsigned int (4 bytes)
    INT64 = "q"   # signed long long (8 bytes)
    UINT64 = "Q"  # unsigned long long (8 bytes)

class RememoryInt:
    """
    A single integer value stored in shared memory, synchronized with a NamedLock.
    Uses binary encoding via struct (default: signed 64-bit).
    """

    def __init__(self, name: str, i_type: IntTypes = IntTypes.INT64):
        """
        :param name: Name of the shared memory block
        :param i_type: IntTypes enum to control bit width and signedness
        """
        self._name = name
        self._iType = i_type
        self._size = struct.calcsize(i_type.value)
        self._shm = None

        try:
            self._shm = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            self._shm = shared_memory.SharedMemory(name=name, create=True, size=self._size)
            self._write_value(0)

        self._lock = NamedLock(name)

    # Internal helpers
    def _read_value(self) -> int:
        if self._shm is None:
            return 0
        data = self._shm.buf[: self._size]
        return struct.unpack(self._iType.value, data)[0]

    def _write_value(self, value: int):
        if self._shm is None:
            return
        packed = struct.pack(self._iType.value, value)
        self._shm.buf[: self._size] = packed

    # Public interface
    @property
    def value(self) -> int:
        with self._lock:
            return self._read_value()

    @value.setter
    def value(self, new_value: int):
        with self._lock:
            self._write_value(new_value)

    def set(self, new_value: int):
        self.value = new_value

    def get(self) -> int:
        return self.value

    def __int__(self) -> int:
        return self.value

    def __repr__(self):
        return f"<RememoryInt {self._name}: {self._read_value()}>"

    def close(self):
        if self._shm is not None:
            self._shm.close()

    def unlink(self):
        if self._shm is not None:
            self._shm.unlink()
