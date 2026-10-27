import re
import time
from pathlib import Path

RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$", re.I)
INVALID_CHARS = re.compile(r'[\x00-\x1f:<>"|?*]')

def relative_target_old(root, value):
    if not isinstance(value, str):
        raise ValueError("FOLDER_PATH_INVALID")
    rel = Path(value)
    if rel.is_absolute() or rel.drive or rel.root:
        raise ValueError("FOLDER_ESCAPE_DENIED")
    for part in rel.parts:
        if part == ".." or part.endswith((" ", ".")) or RESERVED.match(part):
            raise ValueError("FOLDER_PATH_INVALID")
        if any(ord(char) < 32 or char in ':<>"|?*' for char in part):
            raise ValueError("FOLDER_PATH_INVALID")
    return root / rel

def relative_target_new(root, value):
    if not isinstance(value, str):
        raise ValueError("FOLDER_PATH_INVALID")
    rel = Path(value)
    if rel.is_absolute() or rel.drive or rel.root:
        raise ValueError("FOLDER_ESCAPE_DENIED")
    for part in rel.parts:
        if part == ".." or part.endswith((" ", ".")) or RESERVED.match(part):
            raise ValueError("FOLDER_PATH_INVALID")
        if INVALID_CHARS.search(part):
            raise ValueError("FOLDER_PATH_INVALID")
    return root / rel

root = Path("C:/test")
test_paths = [
    "subfolder/documents/report.pdf",
    "a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p/q/r/s/t/u/v/w/x/y/z.txt",
    "images/photo_2023_01_01.jpeg",
    "code/src/computer/folder_paths.py",
    "very_long_folder_name_with_many_characters_1234567890/file_with_a_long_name.extension"
]

N = 100000

t0 = time.perf_counter()
for _ in range(N):
    for p in test_paths:
        relative_target_old(root, p)
t1 = time.perf_counter()
old_time = t1 - t0

t0 = time.perf_counter()
for _ in range(N):
    for p in test_paths:
        relative_target_new(root, p)
t1 = time.perf_counter()
new_time = t1 - t0

print(f"Old time: {old_time:.4f}s")
print(f"New time: {new_time:.4f}s")
print(f"Speedup: {((old_time - new_time) / old_time) * 100:.2f}%")
