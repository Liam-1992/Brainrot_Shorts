from __future__ import annotations

from typing import Optional


def detect_vram_gb() -> Optional[float]:
    try:
        import torch  # type: ignore

        if not torch.cuda.is_available():
            return None
        props = torch.cuda.get_device_properties(0)
        return round(props.total_memory / (1024**3), 2)
    except Exception:
        return None

