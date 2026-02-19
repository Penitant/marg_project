from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EngineConfig:
    grid_rows: int = 4
    grid_cols: int = 4
    tick_interval: float = 1.0
    corridor_depth: int = 3
    reservation_timeout: int = 10
    deadlock_check_interval: int = 5
    revocation_cooldown_ticks: int = 3
    wait_alpha: float = 0.01
    priority_hysteresis_margin: float = 0.05
    default_phase_duration: int = 30
    yellow_phase_duration: int = 5
    min_reservation_hold_ticks: int = 2
    max_retry_before_replan: int = 3
    alpha: float = 0.7
    beta: float = 0.3
    congestion_jitter: float = 0.03
    min_congestion_factor: float = 0.2
    peak_multiplier: float = 1.2
    snapshot_broadcast_interval: int = 2
