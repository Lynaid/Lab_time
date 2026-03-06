# combat/artillery.py
import pygame
import settings


class ArtilleryShell:
    """
    Backward compatible artillery shell.

    Supports creation styles:
      ArtilleryShell(target_pos=..., damage=..., radius=..., mark_time=..., stun=..., big=...)
      ArtilleryShell(target=..., damage=..., radius=..., mark_time=..., stun=..., big=...)
      ArtilleryShell(pygame.Vector2(...), damage, radius, mark_time, stun=..., big=...)
    """

    def __init__(
        self,
        target=None,
        damage: int | None = None,
        radius: float | None = None,
        mark_time: float | None = None,
        stun: float = 0.0,
        big: bool = False,
        **kwargs,
    ):
        # --- Backward compatibility for keyword name ---
        # abilities.py uses target_pos=...
        if target is None and "target_pos" in kwargs:
            target = kwargs.pop("target_pos")

        # Also tolerate "pos"/"center" just in case
        if target is None and "pos" in kwargs:
            target = kwargs.pop("pos")
        if target is None and "center" in kwargs:
            target = kwargs.pop("center")

        if target is None:
            raise TypeError("ArtilleryShell requires target/target_pos Vector2")

        # Convert target to Vector2 safely
        if isinstance(target, pygame.Vector2):
            self.target = pygame.Vector2(float(target.x), float(target.y))
        else:
            # assume tuple-like
            self.target = pygame.Vector2(float(target[0]), float(target[1]))

        if damage is None:
            if "dmg" in kwargs:
                damage = kwargs.pop("dmg")
            else:
                raise TypeError("ArtilleryShell requires damage")

        if radius is None:
            if "r" in kwargs:
                radius = kwargs.pop("r")
            else:
                raise TypeError("ArtilleryShell requires radius")

        if mark_time is None:
            if "mark" in kwargs:
                mark_time = kwargs.pop("mark")
            else:
                raise TypeError("ArtilleryShell requires mark_time")

        self.damage = int(damage)
        self.radius = float(radius)
        self.mark_time = float(mark_time)
        self.stun = float(stun)
        self.big = bool(big)

        self.timer = 0.0
        self.alive = True

        # Visual
        self.impact_flash = 0.0
        self.impact_flash_time = 0.12 if not self.big else 0.16

        # One-tick damage window + guard
        self._damage_window = False
        self._applied = False

    def should_deal_damage_now(self) -> bool:
        """
        Backward compatibility for old main.py loop.
        True only on the exact tick when mark -> impact happens.
        """
        return bool(self._damage_window)

    def try_apply(self, enemies: list) -> bool:
        """
        New API: applies damage/stun once, exactly when impact begins.
        Returns True if damage was applied on this call.
        """
        if self._applied:
            return False
        if not self._damage_window:
            return False

        self._applied = True

        center = self.target
        r = float(self.radius)
        dmg = int(self.damage)
        stun = float(self.stun)

        for e in enemies:
            if not getattr(e, "alive", True):
                continue
            if pygame.Vector2(e.rect.center).distance_to(center) <= r:
                if hasattr(e, "take_projectile_hit"):
                    e.take_projectile_hit(dmg)
                else:
                    # last-resort fallback
                    if hasattr(e, "hp"):
                        e.hp -= dmg
                        if e.hp <= 0:
                            e.alive = False

                if stun > 0.0 and hasattr(e, "apply_stun"):
                    e.apply_stun(stun)

        return True

    def update(self, dt: float):
        if not self.alive:
            return

        # active only for one tick
        self._damage_window = False

        self.timer += float(dt)

        # MARK phase
        if self.timer < self.mark_time:
            return

        # First tick of IMPACT
        if self.impact_flash <= 0.0:
            self.impact_flash = self.impact_flash_time
            self._damage_window = True
            return

        # IMPACT phase
        self.impact_flash -= float(dt)
        if self.impact_flash <= 0.0:
            self.alive = False

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return

        # MARK: shadow
        if self.timer < self.mark_time:
            pygame.draw.circle(
                screen,
                settings.SHADOW_COLOR,
                (int(self.target.x), int(self.target.y)),
                int(self.radius),
                0,
            )
            return

        # IMPACT: flash
        if self.impact_flash > 0.0:
            pygame.draw.circle(
                screen,
                settings.IMPACT_COLOR,
                (int(self.target.x), int(self.target.y)),
                int(self.radius),
                0,
            )
            if self.big:
                pygame.draw.circle(
                    screen,
                    (0, 0, 0),
                    (int(self.target.x), int(self.target.y)),
                    int(self.radius),
                    3,
                )