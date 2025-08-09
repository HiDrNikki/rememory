# Rememory

Rememory provides **shared-memory data structures** (`RememoryDict`, `RememoryList`, and `RememorySet`) as well as basic types (`str`, `int`, `float`, and `bool`) that work safely across multiple processes – even across completely independent Python interpreters – using OS-level named locks.

This is designed for scenarios where you need a simple, Python-native way to share structured state between processes without relying on an external database or message broker. Data is serialized in shared memory using Python's pickle format.

## Features

* **Shared-memory backend** using `multiprocessing.shared_memory`
* **Cross-process synchronization** with OS-level locks (Windows mutex / POSIX semaphore)
* Works across separate scripts and interpreters, not just `multiprocessing.Process`
* Drop-in replacements for `str`, `int`, `float`, `bool`, `Dict`, `List` and `Set`
* Type-safe generics for editors and type checkers (e.g. `RememoryDict[str, int]`)


## Installation

```bash
pip install rememory
```

## Dependencies

On **Linux/macOS** `posix_ipc`, on **Windows** `pywin32`:


## Basic Usage

### RememoryDict

```python
from rememory import Dict # RMDict, or RememoryDict also work

# Create or attach to a shared dict
shared: Dict[str, dict[str, int]] = Dict("game_state")

# Write to it (any process using the same name sees these changes)
shared["player1"] = {"score": 10, "level": 2}

# Read from it
print(shared["player1"])

# Iterate
for key, value in shared.items():
    print(key, value)
```

Any process that does `Dict("game_state")` will connect to the same shared memory block.

### RememoryList

```python
from rememory import List # RMList, or RememoryList also work

shared_list: List[str] = List("chat")

# Append items
shared_list.append("hello")
shared_list.append("world")

# Read
print(shared_list[0])  # "hello"
for item in shared_list:
    print(item)
```

### RememorySet

```python
from rememory import Set # RMSet, or RememorySet also work

shared_set: Set[str] = Set("unique_items")

# Add items
shared_set.add("apple")
shared_set.add("banana") 
shared_set.add("apple")  # Duplicate, won't be added

# Check membership
if "apple" in shared_set:
    print("Found apple!")

# Remove items
shared_set.discard("banana")  # Safe removal
shared_set.remove("apple")    # Raises KeyError if not found

# Set operations
other_items = {"cherry", "date"}
shared_set.update(other_items)  # Union update

# Iterate
for item in shared_set:
    print(item)
```
### RememoryInt
```python
from rememory import int, IntTypes # RMInt, or RememoryInt also work

counter = int("shared_counter", IntTypes.INT32)

counter.value = 42

print(counter.value)  # 42
```
### RememoryFloat
```python
from rememory import float, FloatTypes # RMFloat, or RememoryFloat also work

pi = float("pi", FloatTypes.FLOAT32)

pi.value = 3.14

print(pi.value)
```
### RememoryBlock
```python
from noexcept import NoBaseException
from rememory import Block, BlockSize

# Store arbitrary pickleable objects in shared memory
class CustomError:
    pass

err_block: Block[CustomError] = Block("err_block", BlockSize.s256)

err_block.value = CustomError("boom")

print(err_block.value)
```
### RememoryString
```python
from rememory import str, BlockSize # RMString, or RememoryString also work

msg = str("message", BlockSize.S128)

msg.value = "Hello"

print(msg.value)
```
### RememoryBool
```python
from rememory import bool

flag = bool("ready")

flag.value = True

print(flag.value)
```

## Multiprocessing Example

```python
from multiprocessing import Process
from rememory import Dict, List, Set

SHARED_DICT = "game"
SHARED_LIST = "events"
SHARED_SET = "players"

def worker():
    d = Dict[str, dict[str, int]](SHARED_DICT)
    pid = str(os.getpid())
    d[pid] = {"score": 1, "level": 1}
    d[pid]["score"] += 1

    l = List[str](SHARED_LIST)
    l.append(f"{pid}-joined")
    
    s = Set[str](SHARED_SET)
    s.add(f"player-{pid}")

if __name__ == "__main__":
    d = Dict[str, dict[str, int]](SHARED_DICT)
    l = List[str](SHARED_LIST)
    s = Set[str](SHARED_SET)

    # Clear previous state
    d._write_data({})
    l._write_data([])
    s._writeData(set())

    procs = [Process(target=worker) for _ in range(4)]
    for p in procs: p.start()
    for p in procs: p.join()

    print("Shared dict:", dict(d.items()))
    print("Shared list:", list(l))
    print("Shared set:", s.copy())
```

## Locking

Rememory uses **OS-named synchronization primitives**:

* **Windows:** Named mutex via `pywin32`
* **Linux/macOS:** POSIX named semaphore via `posix_ipc`

This ensures that even **separate Python scripts** respect locking when using the same shared memory name.

## When to Use

* Game engines or simulations needing shared state between processes
* Multi-process pipelines without a heavy DB or broker
* Debugging tools that need live shared state

## When Not to Use

* When your data doesn’t fit in memory
* When you need persistence beyond process lifetime (shared memory is volatile)


## License

This project is released under the **MIT License**. See the [LICENSE](LICENSE) file for details.


## Author

Nichola Walch <littler.compression@gmail.com>