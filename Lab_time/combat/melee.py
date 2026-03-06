# combat/melee.py
import pygame
import settings


class MeleeWeapon:
    def __init__(self, weapon_id: str):
        self.weapon_id = weapon_id

        self.damage = 0
        self.range = 0
        self.windup = 0.0
        self.active = 0.0
        self.cooldown = 0.0

        # extras
        self.knockback = 0.0
        self.knockback_time = 0.0
        self.can_break_walls = False

        self._state = "ready"  # ready -> windup -> active -> cooldown
        self._timer = 0.0

        self.swing_id = 0
        self._last_dir = pygame.Vector2(0, 1)

        self.set_weapon(weapon_id)

    def set_weapon(self, weapon_id: str):
        self.weapon_id = weapon_id
        data = settings.WEAPONS[weapon_id]

        self.damage = int(data["damage"])
        self.range = int(data["range"])
        self.windup = float(data["windup"])
        self.active = float(data["active"])
        self.cooldown = float(data["cooldown"])

        # defaults
        self.knockback = 0.0
        self.knockback_time = 0.0
        self.can_break_walls = False

        if weapon_id == "bat":
            self.knockback = float(settings.BAT_KNOCKBACK)
            self.knockback_time = float(settings.BAT_KNOCKBACK_TIME)

        if weapon_id == "hammer":
            self.can_break_walls = True

        self._state = "ready"
        self._timer = 0.0

    def try_attack(self, attack_dir: pygame.Vector2):
        if self._state != "ready":
            return
        if attack_dir.length_squared() == 0:
            return
        self.remember_dir(attack_dir)
        self._state = "windup"
        self._timer = self.windup
        self.swing_id += 1

    def update(self, dt: float):
        if self._state == "ready":
            return

        self._timer -= dt
        if self._timer > 0:
            return

        if self._state == "windup":
            self._state = "active"
            self._timer = self.active
        elif self._state == "active":
            self._state = "cooldown"
            self._timer = self.cooldown
        elif self._state == "cooldown":
            self._state = "ready"
            self._timer = 0.0

    def is_active(self) -> bool:
        return self._state == "active"

    def remember_dir(self, attack_dir: pygame.Vector2):
        if attack_dir.length_squared() > 0:
            self._last_dir = attack_dir.normalize()
        else:
            self._last_dir = pygame.Vector2(0, 1)

    def _thickness(self) -> int:
        if self.weapon_id == "club":
            return int(getattr(settings, "HITBOX_CLUB_THICKNESS", 26))
        if self.weapon_id == "bat":
            return int(getattr(settings, "HITBOX_BAT_THICKNESS", 62))
        # hammer or default
        return int(getattr(settings, "HITBOX_HAMMER_THICKNESS", getattr(settings, "HITBOX_THICKNESS", 38)))

    def build_hitboxes(self, player_rect: pygame.Rect) -> list[pygame.Rect]:
        """
        Returns a list of hitboxes.
        club: single small rect.
        bat: 2 rects (forward + flank) to simulate a wide swing.
        hammer: single rect like club.
        """
        cx, cy = player_rect.center
        d = pygame.Vector2(self._last_dir)
        if d.length_squared() == 0:
            d = pygame.Vector2(0, 1)
        d = d.normalize()

        thick = self._thickness()
        r = int(self.range)

        rects: list[pygame.Rect] = []

        # main rect in front of player
        if abs(d.x) > abs(d.y):
            # left/right
            if d.x > 0:
                main = pygame.Rect(player_rect.right, cy - thick // 2, r, thick)
            else:
                main = pygame.Rect(player_rect.left - r, cy - thick // 2, r, thick)
        else:
            # up/down
            if d.y > 0:
                main = pygame.Rect(cx - thick // 2, player_rect.bottom, thick, r)
            else:
                main = pygame.Rect(cx - thick // 2, player_rect.top - r, thick, r)

        rects.append(main)

        # bat sweep: add flank rect perpendicular to swing direction
        if self.weapon_id == "bat":
            side_len = int(r * 0.70)
            side_thick = int(thick * 0.70)

            # perpendicular vector
            perp = pygame.Vector2(d.y, -d.x)

            # flank position: slightly forward and to the side (arc simulation)
            offset_fwd = d * (r * 0.35)
            offset_side = perp * (thick * 0.35)

            c2 = pygame.Vector2(cx, cy) + offset_fwd + offset_side

            if abs(perp.x) > abs(perp.y):
                # horizontal flank
                flank = pygame.Rect(int(c2.x - side_len / 2), int(c2.y - side_thick / 2), side_len, side_thick)
            else:
                # vertical flank
                flank = pygame.Rect(int(c2.x - side_thick / 2), int(c2.y - side_len / 2), side_thick, side_len)

            rects.append(flank)

        return rects

    def draw_hitboxes_debug(self, screen: pygame.Surface, player_rect: pygame.Rect):
        if not bool(getattr(settings, "DEBUG_MELEE_HITBOX", False)):
            return
        if not self.is_active():
            return
        for r in self.build_hitboxes(player_rect):
            pygame.draw.rect(screen, (255, 255, 255), r, 2)