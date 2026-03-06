# combat/effects.py
import pygame
import settings


class Effect:
    def __init__(self):
        self.alive = True

    def update(self, dt: float, enemies: list):
        raise NotImplementedError

    def draw(self, screen: pygame.Surface):
        raise NotImplementedError


class AtomicBlastEffect(Effect):
    def __init__(self, center: pygame.Vector2, radius: float, damage: int, visual_time: float):
        super().__init__()
        self.center = pygame.Vector2(float(center.x), float(center.y))
        self.radius = float(radius)
        self.damage = int(damage)
        self.timer = float(visual_time)

        self._applied = False
        self._id = (id(self) & 0x7FFFFFFF)

    def update(self, dt: float, enemies: list):
        if not self.alive:
            return

        if not self._applied:
            r = float(self.radius)
            c = self.center
            dmg = int(self.damage)
            bid = int(self._id)

            for e in enemies:
                if not getattr(e, "alive", True):
                    continue
                if pygame.Vector2(e.rect.center).distance_to(c) <= r:
                    if hasattr(e, "take_blast_hit"):
                        e.take_blast_hit(dmg, bid)
                    elif hasattr(e, "take_projectile_hit"):
                        e.take_projectile_hit(dmg)

            self._applied = True

        self.timer -= float(dt)
        if self.timer <= 0.0:
            self.alive = False

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return
        pygame.draw.circle(
            screen,
            settings.ULT_COLOR,
            (int(self.center.x), int(self.center.y)),
            int(self.radius),
            width=3,
        )
