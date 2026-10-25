"""Captura restrita à janela atribuída, sem capturar o desktop inteiro."""

from __future__ import annotations

import base64
import io
from typing import Optional

from PIL import ImageGrab

from .window_assignments import window_assignments


def capture(session_id: str, hwnd: Optional[int] = None, format: str = "png") -> dict:
    lease = window_assignments.get(session_id)
    if lease is None:
        raise ValueError("TARGET_NOT_ASSIGNED: atribuição humana necessária")
    target = window_assignments.validate(lease)
    if hwnd is not None and int(hwnd) != target:
        raise ValueError("TARGET_NOT_ASSIGNED: HWND não pertence à sessão")
    image = ImageGrab.grab(window=target)
    output = io.BytesIO()
    extension = "JPEG" if format.lower() in ("jpg", "jpeg") else "PNG"
    image.save(output, format=extension)
    window_assignments.validate(lease)
    return {"imageBase64": base64.b64encode(output.getvalue()).decode("ascii"), "width": image.width, "height": image.height, "format": extension.lower(), "targetHwnd": target}
