"""CPU/RAM/GPU/VRAM sampler used by the LLM test mode.

A background thread polls psutil + nvidia-smi at ~5 Hz and produces a peak/avg
summary at the end. Designed to be cheap enough to wrap around a single LLM
call without skewing it.
"""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

import psutil


@dataclass
class MetricSnapshot:
    timestamp: float
    cpu_percent: float
    ram_used_mb: float
    ram_percent: float
    gpu_util_percent: Optional[float] = None
    vram_used_mb: Optional[float] = None
    vram_total_mb: Optional[float] = None


@dataclass
class MetricSummary:
    cpu_peak_percent: float = 0.0
    cpu_avg_percent: float = 0.0
    ram_peak_mb: float = 0.0
    ram_peak_percent: float = 0.0
    gpu_peak_percent: Optional[float] = None
    gpu_avg_percent: Optional[float] = None
    vram_peak_mb: Optional[float] = None
    vram_total_mb: Optional[float] = None
    samples: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def read_nvidia_smi() -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Return (gpu_util%, vram_used_mb, vram_total_mb), or all-None if absent."""
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=2.0,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None, None, None
        first_line = proc.stdout.strip().splitlines()[0]
        gpu_util, mem_used, mem_total = (x.strip() for x in first_line.split(","))
        return float(gpu_util), float(mem_used), float(mem_total)
    except Exception:
        return None, None, None


@dataclass
class SystemMetricsSampler:
    """Start, do work, stop. `stop()` returns the summary."""

    interval_s: float = 0.2
    snapshots: list[MetricSnapshot] = field(default_factory=list)
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self.snapshots.clear()
        self._stop.clear()
        # Prime psutil so the first cpu_percent reading is meaningful.
        psutil.cpu_percent(interval=None)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> MetricSummary:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        return self.summary()

    def _run(self) -> None:
        while not self._stop.is_set():
            vm = psutil.virtual_memory()
            gpu_util, vram_used, vram_total = read_nvidia_smi()
            self.snapshots.append(
                MetricSnapshot(
                    timestamp=time.time(),
                    cpu_percent=psutil.cpu_percent(interval=None),
                    ram_used_mb=vm.used / 1024 / 1024,
                    ram_percent=vm.percent,
                    gpu_util_percent=gpu_util,
                    vram_used_mb=vram_used,
                    vram_total_mb=vram_total,
                )
            )
            time.sleep(self.interval_s)

    def summary(self) -> MetricSummary:
        if not self.snapshots:
            return MetricSummary()

        cpu = [s.cpu_percent for s in self.snapshots]
        ram = [s.ram_used_mb for s in self.snapshots]
        ram_pct = [s.ram_percent for s in self.snapshots]
        gpu = [s.gpu_util_percent for s in self.snapshots if s.gpu_util_percent is not None]
        vram = [s.vram_used_mb for s in self.snapshots if s.vram_used_mb is not None]
        vram_total = [
            s.vram_total_mb for s in self.snapshots if s.vram_total_mb is not None
        ]

        return MetricSummary(
            cpu_peak_percent=max(cpu),
            cpu_avg_percent=sum(cpu) / len(cpu),
            ram_peak_mb=max(ram),
            ram_peak_percent=max(ram_pct),
            gpu_peak_percent=max(gpu) if gpu else None,
            gpu_avg_percent=(sum(gpu) / len(gpu)) if gpu else None,
            vram_peak_mb=max(vram) if vram else None,
            vram_total_mb=max(vram_total) if vram_total else None,
            samples=len(self.snapshots),
        )
