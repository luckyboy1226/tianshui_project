"""Measure one local GeoTIFF NDVI calculation without changing project data."""

import argparse
import ctypes
import json
import os
import sys
import time
from pathlib import Path
from ctypes import wintypes

import django
import numpy as np


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tianshuipy.settings")
django.setup()

from environment.ecological_indices import EcologicalIndexCalculator  # noqa: E402


def peak_working_set_mb():
    """Return the current process peak working set on Windows when available."""
    if os.name != "nt":
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.windll.kernel32
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    process = kernel32.GetCurrentProcess()
    get_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory_info.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    get_memory_info.restype = wintypes.BOOL
    ok = get_memory_info(
        process, ctypes.byref(counters), counters.cb
    )
    return round(counters.PeakWorkingSetSize / 1024 / 1024, 2) if ok else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Absolute path to a GeoTIFF image")
    args = parser.parse_args()

    calculator = EcologicalIndexCalculator(args.image)
    started_at = time.perf_counter()
    loaded = calculator.load_image()
    load_seconds = time.perf_counter() - started_at
    if not loaded:
        raise RuntimeError("The image could not be loaded.")

    started_at = time.perf_counter()
    ndvi = calculator.calculate_ndvi()
    calculate_seconds = time.perf_counter() - started_at
    if ndvi is None:
        raise RuntimeError("NDVI calculation returned no result.")

    valid_values = ndvi[np.isfinite(ndvi)]
    print(json.dumps({
        "image": str(Path(args.image)),
        "image_size_mb": round(Path(args.image).stat().st_size / 1024 / 1024, 2),
        "bands": int(calculator.bands.shape[0]),
        "width": int(calculator.bands.shape[2]),
        "height": int(calculator.bands.shape[1]),
        "load_seconds": round(load_seconds, 3),
        "ndvi_seconds": round(calculate_seconds, 3),
        "total_seconds": round(load_seconds + calculate_seconds, 3),
        "peak_working_set_mb": peak_working_set_mb(),
        "valid_pixel_count": int(valid_values.size),
        "ndvi_min": float(np.min(valid_values)),
        "ndvi_max": float(np.max(valid_values)),
        "ndvi_mean": float(np.mean(valid_values)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
