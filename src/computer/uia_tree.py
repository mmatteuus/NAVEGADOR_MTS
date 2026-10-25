"""Percurso limitado da árvore UIA para evitar enumeração sem limite."""

from __future__ import annotations

from collections import deque


def bounded_children(root, limit: int = 200, max_depth: int = 12):
    queue = deque([(root, 0)])
    seen = 0
    while queue and seen < limit:
        control, depth = queue.popleft()
        if control is not root:
            yield control
            seen += 1
        if depth >= max_depth:
            continue
        try:
            children = control.children()
        except Exception:
            children = []
        room = max(0, limit - seen - len(queue))
        queue.extend((child, depth + 1) for child in children[:room])
