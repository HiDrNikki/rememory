from multiprocessing import shared_memory
from .namedLock import NamedLock

class RememoryBool:
    """
    A single boolean value stored in shared memory, synchronized with a NamedLock.
    Stores 1 byte (0 or 1).
    """

    def __init__(self, name: str):
        self._name = name
        self._size = 1  # 1 byte is enough
        self._shm = None

        # Try to attach; if it doesn't exist, create it
        try:
            self._shm = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            self._shm = shared_memory.SharedMemory(name=name, create=True, size=self._size)
            self._write_value(False)

        self._lock = NamedLock(name)

    # Internal helpers
    def _read_value(self) -> bool:
        if self._shm is None:
            return False
        return bool(self._shm.buf[0])

    def _write_value(self, value: bool):
        if self._shm is None:
            return
        self._shm.buf[0] = 1 if value else 0

    # Public interface
    @property
    def value(self) -> bool:
        with self._lock:
            return self._read_value()

    @value.setter
    def value(self, new_value: bool):
        with self._lock:
            self._write_value(new_value)

    def set(self, new_value: bool):
        self.value = new_value

    def get(self) -> bool:
        return self.value

    def __bool__(self) -> bool:
        return self.value

    def __repr__(self):
        return f"<RememoryBool {self._name}: {self._read_value()}>"

    def close(self):
        if self._shm is not None:
            self._shm.close()

    def unlink(self):
        if self._shm is not None:
            self._shm.unlink()
