# combat/status_effects.py
import pygame


class StatusEffect:
    def __init__(self, duration: float):
        self.duration = float(duration)
        self.timer = float(duration)
        self.alive = True

    def update(self, dt: float, owner):
        raise NotImplementedError

    def expire(self):
        self.alive = False


class Poison(StatusEffect):
    def __init__(self, duration: float, tick_interval: float, damage: int):
        super().__init__(duration)
        self.tick_interval = float(tick_interval)
        self.damage = int(damage)
        self._tick_timer = self.tick_interval

    def update(self, dt: float, owner):
        if not self.alive:
            return

        self.timer -= dt
        self._tick_timer -= dt

        if self._tick_timer <= 0.0:
            if hasattr(owner, "take_projectile_hit"):
                owner.take_projectile_hit(self.damage)
            self._tick_timer += self.tick_interval

        if self.timer <= 0.0:
            self.expire()


class Freeze(StatusEffect):
    def __init__(self, duration: float, slow_mult: float):
        super().__init__(duration)
        self.slow_mult = max(0.05, min(1.0, float(slow_mult)))
        self._applied = False
        self._orig_speed: float | None = None

    def _apply_once(self, owner):
        if self._applied:
            return
        if not hasattr(owner, "speed"):
            self._applied = True
            return

        try:
            self._orig_speed = float(owner.speed)
            owner.speed = float(owner.speed) * self.slow_mult
        except Exception:
            self._orig_speed = None
        self._applied = True

    def _revert_once(self, owner):
        if not self._applied:
            return
        if self._orig_speed is None:
            return
        if not hasattr(owner, "speed"):
            return
        try:
            owner.speed = float(self._orig_speed)
        except Exception:
            pass

    def update(self, dt: float, owner):
        if not self.alive:
            return

        self._apply_once(owner)

        self.timer -= dt
        if self.timer <= 0.0:
            self._revert_once(owner)
            self.expire()