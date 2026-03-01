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
    TONE_ARM_RECORD_END_STEPS,
    TONE_ARM_RECORD_START_STEPS,
    TONE_ARM_STEPS_PER_REV,
    TURNTABLE_TARGET_RPM,
    TURNTABLE_TARGET_STEPS_PER_SEC,
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

    def _step_tone_arm(self, direction: int, update_steps: bool = True) -> None:
        """Advance tone-arm one half-step (physical rotation inverted vs step sign).
        When update_steps is False (e.g. from Settings calibration), only the motor moves; _tone_arm_steps is not updated.
        """
        if update_steps:
            self._tone_arm_steps += direction
        if self._simulate:
            return
        seq = HALF_STEP_SEQUENCE
        idx = self._tone_arm_sequence_index
        idx = (idx + direction) % len(seq)  # inverted so positive steps = toward end of record
        self._tone_arm_sequence_index = idx
        for i, pin in enumerate(PIN_TONE_ARM):
            GPIO.output(pin, seq[idx][i])

    def get_tone_arm_position(self) -> ToneArmPosition:
        """Return current tone-arm position (steps_from_home: positive = toward end of record)."""
        with self._lock:
            # Report inverted so API/calibration see positive = toward end
            steps = -self._tone_arm_steps
            angle = (steps / TONE_ARM_STEPS_PER_REV) * 360.0
            return ToneArmPosition(
                steps_from_home=steps,
                total_steps_per_rev=TONE_ARM_STEPS_PER_REV,
                current_angle_deg=angle,
            )

    def move_tone_arm(self, steps: int, absolute: bool = False, from_settings: bool = False) -> None:
        """Move tone-arm by steps (relative) or to steps (absolute). Blocking with accel.

        Steps are in 'steps_from_home': 0 = home, positive = toward end of record.
        When from_settings is True (Settings calibration), the motor moves but _tone_arm_steps is not
        updated, so the logical position is unchanged and you can correct the physical home without
        losing sync.
        """
        update_steps = not from_settings
        with self._lock:
            # External steps: 0 = home, positive = toward end. Internal _tone_arm_steps is inverted.
            target_ext = steps if absolute else (-self._tone_arm_steps + steps)
            target = max(-TONE_ARM_MAX_STEPS, min(TONE_ARM_MAX_STEPS, -target_ext))
        delta = target - self._tone_arm_steps
        if delta == 0 and not from_settings:
            return
        if from_settings:
            # Relative move only: steps is the delta; we don't update internal position
            steps_to_move = abs(steps)
            direction = 1 if steps > 0 else -1
            if steps_to_move == 0:
                return
        else:
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
            self._step_tone_arm(direction, update_steps=update_steps)
            time.sleep(delay_for_step(i))

    def move_tone_arm_to_angle(self, angle_deg: float) -> None:
        """Move tone-arm to angle (0 = home)."""
        steps = int((angle_deg / 360.0) * TONE_ARM_STEPS_PER_REV)
        steps = max(-TONE_ARM_MAX_STEPS, min(TONE_ARM_MAX_STEPS, steps))
        self.move_tone_arm(steps, absolute=True)

    def sync_tone_arm_to_fraction(self, fraction: float) -> None:
        """Move tone-arm so that 0.0 = start of record and 1.0 = end-of-record arc.

        Fraction is playlist position in [0, 1]. Target steps are in steps_from_home
        (0 = home, positive = toward end). Uses TONE_ARM_RECORD_START_STEPS and/or
        TONE_ARM_RECORD_END_STEPS when set (so we never ignore a calibrated bound);
        defaults to 0 and TONE_ARM_MAX_STEPS for any unset bound. Uses round() for
        fraction->steps to avoid systematic truncation.
        """
        f = max(0.0, min(1.0, fraction))
        start_step = (
            TONE_ARM_RECORD_START_STEPS
            if TONE_ARM_RECORD_START_STEPS is not None
            else 0
        )
        end_step = (
            TONE_ARM_RECORD_END_STEPS
            if TONE_ARM_RECORD_END_STEPS is not None
            else TONE_ARM_MAX_STEPS
        )
        target_steps = int(round(start_step + f * (end_step - start_step)))
        target_steps = max(-TONE_ARM_MAX_STEPS, min(TONE_ARM_MAX_STEPS, target_steps))
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
        if speed_rpm is not None:
            target_speed = self._rpm_to_steps_per_sec(speed_rpm)
        else:
            target_speed = TURNTABLE_TARGET_STEPS_PER_SEC
        with self._lock:
            if self._turntable_spinning:
                self._turntable_direction = 1
                self._turntable_target_speed_steps_per_sec = target_speed
                return
            self._turntable_stop_requested = False
            self._turntable_direction = 1
            self._turntable_target_speed_steps_per_sec = target_speed
            self._turntable_current_speed = target_speed  # instant speed, skip ramp
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
