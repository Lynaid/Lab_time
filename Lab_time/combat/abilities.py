# combat/abilities.py
import pygame
import random
import math
import settings

from combat.projectile import Projectile
from combat.artillery import ArtilleryShell
from combat.effects import AtomicBlastEffect


class Ability:
    """
      - self.cooldown (float) 
      - self.timer
      - ready/update_cd/trigger/cooldown_ratio
      - base_cooldown + cooldown_mult
      - trigger()  timer  cooldown
    """
    def __init__(self, cooldown: float):
        self.base_cooldown = float(cooldown)
        self.cooldown_mult = 1.0

        # keep legacy field
        self.cooldown = float(cooldown)
        self.timer = 0.0

    def _recalc_cooldown(self) -> float:
        return max(0.01, self.base_cooldown * float(self.cooldown_mult))

    def ready(self) -> bool:
        return self.timer <= 0.0

    def update_cd(self, dt: float):
        if self.timer > 0.0:
            self.timer -= dt

    def trigger(self):
        cd = self._recalc_cooldown()
        self.cooldown = cd
        self.timer = cd

    def cooldown_ratio(self) -> float:
        cd = float(self.cooldown)
        if cd <= 0:
            return 1.0
        return 1.0 - max(0.0, self.timer) / cd


class FastShot(Ability):
    # Q
    def __init__(self):
        super().__init__(settings.Q_COOLDOWN)
        self.improved = False

        # MODS
        self.bonus_damage = 0
        self.force_piercing = False
        self.force_trail = False

    def cast(self, player, projectiles: list):
        if not self.ready():
            return

        direction = player.attack_dir
        if direction.length_squared() == 0:
            direction = pygame.Vector2(0, 1)

        if self.improved:
            dmg = int(settings.Q_IMPROVED_DAMAGE)
            piercing = bool(settings.Q_IMPROVED_PIERCING)
            trail = bool(settings.Q_IMPROVED_TRAIL)
        else:
            dmg = int(settings.Q_DAMAGE)
            piercing = False
            trail = False

        dmg += int(self.bonus_damage)
        piercing = piercing or bool(self.force_piercing)
        trail = trail or bool(self.force_trail)

        projectiles.append(Projectile(player.rect.center, direction, dmg, piercing=piercing, trail=trail))
        self.trigger()


class BulletCycle(Ability):
    # R
    def __init__(self):
        super().__init__(settings.R_COOLDOWN)
        self.storm = False

        self.queue_left = 0
        self.queue_timer = 0.0
        self.queue_dir = pygame.Vector2(0, 1)

        # MODS (для апгрейдов)
        self.bonus_damage = 0
        self.bonus_count = 0
        self.interval_mult = 1.0

        # runtime (обновляются при cast)
        self.damage = int(settings.R_DAMAGE)
        self.interval = float(settings.R_INTERVAL)
        self.count = int(settings.R_BULLETS)

    def cast(self, player):
        if not self.ready():
            return False

        d = player.attack_dir
        if d.length_squared() == 0:
            d = pygame.Vector2(0, 1)
        self.queue_dir = d.normalize()

        if self.storm:
            base_count = int(settings.R_STORM_BULLETS)
            base_damage = int(settings.R_STORM_DAMAGE)
            base_interval = float(settings.R_STORM_INTERVAL)
        else:
            base_count = int(settings.R_BULLETS)
            base_damage = int(settings.R_DAMAGE)
            base_interval = float(settings.R_INTERVAL)

        # APPLY MODS (персистентные)
        self.count = max(1, base_count + int(self.bonus_count))
        self.damage = max(0, base_damage + int(self.bonus_damage))
        self.interval = max(0.01, base_interval * float(self.interval_mult))

        self.queue_left = self.count
        self.queue_timer = 0.0

        self.trigger()
        return True

    def update(self, dt: float, player, projectiles: list):
        self.update_cd(dt)

        if self.queue_left <= 0:
            return

        self.queue_timer -= dt
        while self.queue_left > 0 and self.queue_timer <= 0.0:
            projectiles.append(Projectile(player.rect.center, self.queue_dir, int(self.damage)))
            self.queue_left -= 1
            self.queue_timer += float(self.interval)


class AtomicBlast(Ability):
    # E
    def __init__(self):
        super().__init__(settings.E_COOLDOWN)

        # base params (can be tuned by upgrades too)
        self.radius = float(settings.ULT_RADIUS)
        self.damage = int(settings.ULT_DAMAGE)
        self.visual_time = 0.20

        # MODS
        self.bonus_radius = 0.0
        self.bonus_damage = 0

    def cast(self, player, effects: list | None = None) -> bool:
        if not self.ready():
            return False

        radius = float(self.radius) + float(self.bonus_radius)
        damage = int(self.damage) + int(self.bonus_damage)

        if effects is not None:
            effects.append(
                AtomicBlastEffect(
                    center=pygame.Vector2(player.rect.center),
                    radius=radius,
                    damage=damage,
                    visual_time=self.visual_time,
                )
            )

        self.trigger()
        return True

    def update(self, dt: float):
        self.update_cd(dt)


class ArtilleryRain(Ability):
    # F
    def __init__(self):
        super().__init__(settings.F_COOLDOWN)
        self.big_salvo = False

        # MODS normal
        self.bonus_shells = 0
        self.bonus_damage = 0
        self.bonus_radius = 0.0
        self.spawn_radius_mult = 1.0

        # MODS big
        self.big_bonus_damage = 0
        self.big_bonus_radius = 0.0
        self.big_bonus_stun = 0.0

    def cast(self, player, artillery_shells: list, bounds: pygame.Rect):
        if not self.ready():
            return False

        center = pygame.Vector2(player.rect.center)

        if self.big_salvo:
            # переключаем базовый кд режима
            self.base_cooldown = float(settings.F_BIG_COOLDOWN)

            radius = float(settings.F_BIG_RADIUS) + float(self.big_bonus_radius)
            damage = int(settings.F_BIG_DAMAGE) + int(self.big_bonus_damage)
            stun = float(settings.F_BIG_STUN) + float(self.big_bonus_stun)

            target = center.copy()
            target.x = max(bounds.left + radius, min(bounds.right - radius, target.x))
            target.y = max(bounds.top + radius, min(bounds.bottom - radius, target.y))

            artillery_shells.append(
                ArtilleryShell(
                    target_pos=target,
                    damage=damage,
                    radius=radius,
                    mark_time=float(settings.F_BIG_MARK_TIME),
                    stun=stun,
                )
            )
        else:
            self.base_cooldown = float(settings.F_COOLDOWN)

            shells = max(1, int(settings.F_SHELLS) + int(self.bonus_shells))
            damage = max(0, int(settings.F_DAMAGE) + int(self.bonus_damage))
            radius = float(settings.F_RADIUS) + float(self.bonus_radius)
            spawn_r = float(settings.F_SPAWN_RADIUS) * float(self.spawn_radius_mult)

            for _ in range(shells):
                ang = random.random() * (2.0 * math.pi)
                t = (random.random() ** 0.5) * spawn_r
                target = center + pygame.Vector2(math.cos(ang), math.sin(ang)) * t

                target.x = max(bounds.left + radius, min(bounds.right - radius, target.x))
                target.y = max(bounds.top + radius, min(bounds.bottom - radius, target.y))

                artillery_shells.append(
                    ArtilleryShell(
                        target_pos=target,
                        damage=damage,
                        radius=radius,
                        mark_time=float(settings.F_MARK_TIME),
                        stun=0.0,
                    )
                )

        self.trigger()
        return True