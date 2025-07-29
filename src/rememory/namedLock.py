import sys
if sys.platform == "win32":
    import win32event
    import win32con
else:
    import posix_ipc

class NamedLock:
    """Cross-platform named lock using OS primitives."""

    def __init__(self, name: str):
        self._name = f"rememorydict_{name}"
        if sys.platform == "win32":
            self._handle = win32event.CreateMutex(None, False, self._name)  # type: ignore
        else:
            # POSIX named semaphore
            self._sem = posix_ipc.Semaphore(f"/{self._name}", flags=posix_ipc.O_CREAT, initial_value=1)

    def __enter__(self):
        if sys.platform == "win32":
            # Wait infinitely
            win32event.WaitForSingleObject(self._handle, win32event.INFINITE)
        else:
            self._sem.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if sys.platform == "win32":
            win32event.ReleaseMutex(self._handle)
        else:
            self._sem.release()
