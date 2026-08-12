"""Backpressure: pause the pipeline while the machine is saturated.

A batch of 20.000 scans will happily starve the workstation it runs on. Before
starting each chunk the pipeline asks whether the machine can take it, and
waits -- bounded -- if it cannot. Bounded, because blocking forever on a
permanently busy machine would be worse than degraded throughput.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import psutil

from ..config import MAX_CPU_PERCENT, MAX_RAM_PERCENT, RESOURCE_WAIT_SECONDS

logger = logging.getLogger(__name__)

_SAMPLE_INTERVAL = 0.3


@dataclass(frozen=True)
class SystemUsage:
    cpu_percent: float
    ram_percent: float

    @property
    def is_saturated(self) -> bool:
        return self.cpu_percent >= MAX_CPU_PERCENT or self.ram_percent >= MAX_RAM_PERCENT


def current_usage(interval: float = 0.1) -> SystemUsage:
    """Instantaneous CPU and RAM usage."""
    return SystemUsage(
        cpu_percent=psutil.cpu_percent(interval=interval),
        ram_percent=psutil.virtual_memory().percent,
    )


def wait_for_resources(max_wait: float = RESOURCE_WAIT_SECONDS) -> bool:
    """Block until the machine is below the CPU/RAM thresholds.

    Returns ``True`` if resources became available, ``False`` if ``max_wait``
    elapsed first (the caller proceeds anyway -- degraded, not stopped).
    """
    deadline = time.monotonic() + max_wait
    waited = False

    while time.monotonic() < deadline:
        usage = current_usage(interval=_SAMPLE_INTERVAL)
        if not usage.is_saturated:
            if waited:
                logger.debug("Recursos disponibles de nuevo, se reanuda el proceso")
            return True
        if not waited:
            logger.info(
                "Sistema saturado (CPU %.0f%%, RAM %.0f%%): esperando…",
                usage.cpu_percent, usage.ram_percent,
            )
            waited = True
        time.sleep(_SAMPLE_INTERVAL)

    logger.warning("Se agotó la espera por recursos; se continúa de todos modos")
    return False
