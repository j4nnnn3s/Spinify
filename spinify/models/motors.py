"""Tone-arm and turntable motor state."""
from dataclasses import dataclass


@dataclass
class ToneArmPosition:
    """Tone-arm position in steps and derived angle."""
    steps_from_home: int
    total_steps_per_rev: int
    current_angle_deg: float


@dataclass
class SpinState:
    """Turntable spin state."""
    is_spinning: bool
    direction: int  # 1 or -1
    current_speed_steps_per_sec: float
    target_speed_steps_per_sec: float
