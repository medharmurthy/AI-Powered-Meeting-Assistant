from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from verbatim.schemas import GpuInfo


def prepare_cuda() -> list[str]:
    """Discover and register CUDA/cuDNN dynamic libraries if present.

    Returns a list of library directory paths.
    On Windows, registers via os.add_dll_directory.
    On Linux, returns paths that should be in LD_LIBRARY_PATH.
    On macOS, returns an empty list.
    """
    system = platform.system().lower()
    discovered_paths: list[str] = []

    if system not in ("windows", "linux"):
        return discovered_paths

    packages = ["nvidia.cublas", "nvidia.cudnn"]
    for pkg in packages:
        try:
            mod = __import__(pkg, fromlist=["__path__"])
            if hasattr(mod, "__path__") and mod.__path__:
                base = Path(mod.__path__[0])
                candidates = [base / "bin", base / "lib"]
                for c in candidates:
                    if c.exists() and c.is_dir():
                        discovered_paths.append(str(c.resolve()))
                        if system == "windows" and hasattr(os, "add_dll_directory"):
                            try:
                                os.add_dll_directory(str(c.resolve()))
                            except Exception:
                                pass
        except Exception:
            pass

    return discovered_paths


def get_gpu_info() -> GpuInfo:
    """Detect available CUDA GPU and its VRAM without requiring torch."""
    cuda_available = False
    device_name: str | None = None
    vram_gb: float | None = None

    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            cuda_available = True
    except Exception:
        pass

    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip()
            if out:
                first_line = out.splitlines()[0]
                parts = [p.strip() for p in first_line.split(",")]
                if len(parts) >= 1 and parts[0]:
                    device_name = parts[0]
                    cuda_available = True
                if len(parts) >= 2:
                    try:
                        mem_mb = float(parts[1])
                        vram_gb = round(mem_mb / 1024.0, 1)
                    except ValueError:
                        pass
        except Exception:
            pass

    return GpuInfo(
        available=cuda_available,
        name=device_name,
        vram_gb=vram_gb,
    )
