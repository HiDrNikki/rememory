import warnings
from .sharedBlock import RememoryBlock, BlockSize

class RememoryString(RememoryBlock[str]):
    """Fixed-size shared UTF-8 string built on RememoryBlock."""

    def __init__(self, name: str, size: BlockSize = BlockSize.s256):
        super().__init__(name, size.value)

    def _read_value(self) -> str:
        raw = self._read_bytes()
        return raw.rstrip(b"\x00").decode("utf-8")

    def _write_value(self, value: str):
        data = value.encode("utf-8")
        if len(data) > self._size:
            warnings.warn(
                f"RememoryString[{self._name}] value too long "
                f"({len(data)} > {self._size}), truncating."
            )
            data = data[: self._size]
        self._write_bytes(data)

    @property
    def value(self) -> str:
        with self._lock:
            return self._read_value()

    @value.setter
    def value(self, new_value: str):
        with self._lock:
            self._write_value(new_value)

    def set(self, new_value: str):
        self.value = new_value

    def get(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value

    def __repr__(self):
        return f"<RememoryString {self._name}: '{self._read_value()}'>"
