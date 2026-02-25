"""Stepper control for turntable and tone-arm with acceleration/deceleration."""
import math
import threading
import time
from typing import Optional

from spinify.config import (
    MOTOR_MAX_DELAY,
    MOTOR_MIN_DELAY,
    PIN_TONE_ARM,
    PIN_TURNTABLE,
    SIMULATE_HARDWARE,
    STEPS_PER_REV,
    TONE_ARM_MAX_STEPS,
    TONE_ARM_STEPS_PER_REV,
    TURNTABLE_TARGET_RPM,
)
from spinify.models.motors import SpinState, ToneArmPosition

# Half-step sequence for 28BYJ-48 (8 steps per cycle)
HALF_STEP_SEQUENCE = [
    (1, 0, 0, 0),
    (1, 1, 0, 0),
    (0, 1, 0, 0),
    (0, 1, 1, 0),
    (0, 0, 1, 0),
    (0, 0, 1, 1),
    (0, 0, 0, 1),
    (1, 0, 0, 1),
]

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    _GPIO_AVAILABLE = False


class MotorService:
    """Controls turntable and tone-arm steppers with acceleration."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._simulate = SIMULATE_HARDWARE or not _GPIO_AVAILABLE

        # Tone-arm state
        self._tone_arm_steps = 0
        self._tone_arm_target_steps: Optional[int] = None
        self._tone_arm_sequence_index = 0

        # Turntable state
        self._turntable_spinning = False
        self._turntable_direction = 1
        self._turntable_current_speed = 0.0
        self._turntable_target_speed_steps_per_sec = 0.0
        self._turntable_sequence_index = 0
        self._turntable_thread: Optional[threading.Thread] = None
        self._turntable_stop_requested = False

        if not self._simulate and _GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            for pin in PIN_TURNTABLE + PIN_TONE_ARM:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)

    def _step_turntable(self, direction: int) -> None:
        """Advance turntable one half-step."""
        if self._simulate:
            return
        seq = HALF_STEP_SEQUENCE
        idx = self._turntable_sequence_index
        idx = (idx + direction) % len(seq)
        self._turntable_sequence_index = idx
        for i, pin in enumerate(PIN_TURNTABLE):
            GPIO.output(pin, seq[idx][i])

    def _step_tone_arm(self, direction: int) -> None:
        """Advance tone-arm one half-step (physical rotation reversed vs step sign)."""
        self._tone_arm_steps += direction
        if self._simulate:
            return
        seq = HALF_STEP_SEQUENCE
        idx = self._tone_arm_sequence_index
        idx = (idx - direction) % len(seq)  # reverse physical direction
        self._tone_arm_sequence_index = idx
        for i, pin in enumerate(PIN_TONE_ARM):
            GPIO.output(pin, seq[idx][i])

    def get_tone_arm_position(self) -> ToneArmPosition:
        """Return current tone-arm position."""
        with self._lock:
            angle = (self._tone_arm_steps / TONE_ARM_STEPS_PER_REV) * 360.0
            return ToneArmPosition(
                steps_from_home=self._tone_arm_steps,
                total_steps_per_rev=TONE_ARM_STEPS_PER_REV,
                current_angle_deg=angle,
            )

    def move_tone_arm(self, steps: int, absolute: bool = False) -> None:
        """Move tone-arm by steps (relative) or to steps (absolute). Blocking with accel."""
        with self._lock:
            target = steps if absolute else self._tone_arm_steps + steps
            target = max(-TONE_ARM_MAX_STEPS, min(TONE_ARM_MAX_STEPS, target))
        delta = target - self._tone_arm_steps
        if delta == 0:
            return
        direction = 1 if delta > 0 else -1
        steps_to_move = abs(delta)
        # Ramp: start slow, speed up, slow down at end
        steps_accel = min(steps_to_move // 3, 50)
        steps_decel = min(steps_to_move // 3, 50)

        def delay_for_step(step_num: int) -> float:
            if step_num < steps_accel and steps_accel > 0:
                t = step_num / steps_accel
                return MOTOR_MAX_DELAY - t * (MOTOR_MAX_DELAY - MOTOR_MIN_DELAY)
            if step_num >= steps_to_move - steps_decel and steps_decel > 0:
                t = (steps_to_move - step_num) / steps_decel
                return MOTOR_MAX_DELAY - t * (MOTOR_MAX_DELAY - MOTOR_MIN_DELAY)
            return MOTOR_MIN_DELAY

        for i in range(steps_to_move):
            self._step_tone_arm(direction)
            time.sleep(delay_for_step(i))

    def move_tone_arm_to_angle(self, angle_deg: float) -> None:
        """Move tone-arm to angle (0 = home)."""
        steps = int((angle_deg / 360.0) * TONE_ARM_STEPS_PER_REV)
        steps = max(-TONE_ARM_MAX_STEPS, min(TONE_ARM_MAX_STEPS, steps))
        self.move_tone_arm(steps, absolute=True)

    def sync_tone_arm_to_fraction(self, fraction: float) -> None:
        """Move tone-arm so that 0.0 = home and 1.0 = end-of-record arc.

        Uses TONE_ARM_MAX_STEPS as the maximum travel from home.
        """
        f = max(0.0, min(1.0, fraction))
        target_steps = int(f * TONE_ARM_MAX_STEPS)
        self.move_tone_arm(target_steps, absolute=True)

    def get_turntable_state(self) -> SpinState:
        """Return current turntable spin state."""
        with self._lock:
            return SpinState(
                is_spinning=self._turntable_spinning,
                direction=self._turntable_direction,
                current_speed_steps_per_sec=self._turntable_current_speed,
                target_speed_steps_per_sec=self._turntable_target_speed_steps_per_sec,
            )

    def _rpm_to_steps_per_sec(self, rpm: float) -> float:
        return rpm * STEPS_PER_REV / 60.0

    def turntable_start(self, direction: int = 1, speed_rpm: Optional[float] = None) -> None:
        """Start turntable with smooth acceleration."""
        rpm = speed_rpm if speed_rpm is not None else TURNTABLE_TARGET_RPM
        target_speed = self._rpm_to_steps_per_sec(rpm)
        with self._lock:
            if self._turntable_spinning:
                self._turntable_direction = direction
                self._turntable_target_speed_steps_per_sec = target_speed
                return
            self._turntable_stop_requested = False
            self._turntable_direction = direction
            self._turntable_target_speed_steps_per_sec = target_speed
            self._turntable_spinning = True
        if self._turntable_thread and self._turntable_thread.is_alive():
            return
        self._turntable_thread = threading.Thread(target=self._turntable_loop, daemon=True)
        self._turntable_thread.start()

    def _turntable_loop(self) -> None:
        """Background loop: accelerate to target speed, maintain until stop, then decelerate."""
        accel = 40.0  # steps/s^2
        dt = 0.02
        while True:
            with self._lock:
                if not self._turntable_spinning or self._turntable_stop_requested:
                    self._turntable_spinning = False
                    self._turntable_current_speed = 0.0
                    if not self._simulate and _GPIO_AVAILABLE:
                        for pin in PIN_TURNTABLE:
                            GPIO.output(pin, GPIO.LOW)
                    return
                target = self._turntable_target_speed_steps_per_sec
                direction = self._turntable_direction
            # Ramp up to target
            while self._turntable_current_speed < target:
                with self._lock:
                    if self._turntable_stop_requested:
                        break
                    self._turntable_current_speed = min(
                        target,
                        self._turntable_current_speed + accel * dt,
                    )
                    speed = self._turntable_current_speed
                self._step_turntable(direction)
                time.sleep(1.0 / speed if speed > 1 else MOTOR_MAX_DELAY)
            # Maintain at target until stop
            while True:
                with self._lock:
                    if self._turntable_stop_requested or self._turntable_target_speed_steps_per_sec <= 0:
                        break
                    speed = self._turntable_current_speed
                self._step_turntable(direction)
                time.sleep(1.0 / speed if speed > 1 else MOTOR_MAX_DELAY)
            # Decelerate to zero
            while self._turntable_current_speed > 0:
                with self._lock:
                    self._turntable_current_speed = max(0, self._turntable_current_speed - accel * dt)
                    speed = self._turntable_current_speed
                self._step_turntable(direction)
                time.sleep(1.0 / speed if speed > 1 else MOTOR_MAX_DELAY)
            with self._lock:
                self._turntable_spinning = False
                self._turntable_current_speed = 0.0
            if not self._simulate and _GPIO_AVAILABLE:
                for pin in PIN_TURNTABLE:
                    GPIO.output(pin, GPIO.LOW)
            return

    def turntable_stop(self) -> None:
        """Stop turntable; background loop will decelerate and stop."""
        with self._lock:
            self._turntable_stop_requested = True
            self._turntable_target_speed_steps_per_sec = 0.0
