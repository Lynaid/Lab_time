# actors/boss.py
import math
import random
import pygame
import settings
from actors.enemy import EnemyBase, EnemyBullet, _rect_center, _los


class BossPhase1(EnemyBase):
    """
    Stable boss implementation:
      - no EnemyAgent
      - uses EnemyBase._move_with_solids
      - attacks: burst / ring / dash (with telegraph)
      - pop_shots() returns list of EnemyBullet
    """

    def __init__(self, x: float, y: float):
        super().__init__(x, y)

        # override size / hp / color
        s = int(getattr(settings, "BOSS_SIZE", 70))
        self.rect = pygame.Rect(int(x - s / 2), int(y - s / 2), s, s)
        self.pos = pygame.Vector2(self.rect.centerx, self.rect.centery)

        self.hp_base = int(getattr(settings, "BOSS_HP_BASE", 240))
        self.hp = self.hp_base

        self._rng = random.Random((int(x) << 16) ^ int(y) ^ 1337)

        # pending bullets
        self._pending: list[EnemyBullet] = []

        # attack cooldowns
        self.burst_cd = 0.8
        self.ring_cd = 1.4
        self.dash_cd = 2.0

        # dash state machine
        self.state = "idle"          # idle / windup / dash
        self.state_t = 0.25
        self.windup_dir = pygame.Vector2(0, 1)
        self.dash_dir = pygame.Vector2(0, 1)

        # tuning
        self.speed = float(getattr(settings, "BOSS_SPEED", 120.0))
        self.dash_speed = float(getattr(settings, "BOSS_DASH_SPEED", 720.0))
        self.dash_time = float(getattr(settings, "BOSS_DASH_TIME", 0.22))
        self.windup_time = float(getattr(settings, "BOSS_DASH_WINDUP", 0.42))

        self.bullet_speed = float(getattr(settings, "BOSS_BULLET_SPEED", 420.0))
        self.bullet_damage = int(getattr(settings, "BOSS_BULLET_DAMAGE", settings.ENEMY_BULLET_DAMAGE))

        self.burst_n = int(getattr(settings, "BOSS_BURST_BULLETS", 6))
        self.burst_spread = float(getattr(settings, "BOSS_BURST_SPREAD_RAD", 0.18))

        self.ring_n = int(getattr(settings, "BOSS_RING_BULLETS", 10))

    def take_projectile_hit(self, dmg: int):
        if not self.alive:
            return
        self.hp -= int(dmg)
        if self.hp <= 0:
            self.alive = False

    def is_dashing(self) -> bool:
        return self.state == "dash"

    def _shoot_burst(self, player_rect: pygame.Rect, solids: list[pygame.Rect]):
        origin = _rect_center(self.rect)
        pc = _rect_center(player_rect)

        v = pc - origin
        if v.length_squared() == 0:
            v = pygame.Vector2(0, 1)
        base = v.normalize()

        # always shoot toward player regardless of LOS
        n = self.burst_n
        spread = self.burst_spread
        mid = (n - 1) / 2.0
        for i in range(n):
            a = (i - mid) * spread
            ca = math.cos(a)
            sa = math.sin(a)
            d = pygame.Vector2(base.x * ca - base.y * sa, base.x * sa + base.y * ca)
            vel = d.normalize() * self.bullet_speed
            self._pending.append(EnemyBullet(origin, vel, self.bullet_damage))

        self.burst_cd = float(getattr(settings, "BOSS_BURST_CD", 1.2))

    def _shoot_ring(self):
        origin = _rect_center(self.rect)
        n = self.ring_n
        for i in range(n):
            ang = (i / n) * 2.0 * math.pi
            d = pygame.Vector2(math.cos(ang), math.sin(ang))
            vel = d * self.bullet_speed
            self._pending.append(EnemyBullet(origin, vel, self.bullet_damage))

        self.ring_cd = float(getattr(settings, "BOSS_RING_CD", 2.2))

    def _start_windup(self, player_rect: pygame.Rect):
        myc = _rect_center(self.rect)
        pc = _rect_center(player_rect)
        d = pc - myc
        if d.length_squared() == 0:
            d = pygame.Vector2(0, 1)
        self.windup_dir = d.normalize()
        self.state = "windup"
        self.state_t = self.windup_time

    def _start_dash(self):
        d = self.windup_dir
        if d.length_squared() == 0:
            d = pygame.Vector2(0, 1)
        self.dash_dir = d.normalize()
        self.state = "dash"
        self.state_t = self.dash_time
        self.dash_cd = float(getattr(settings, "BOSS_DASH_CD", 2.4))

    def pop_shots(self, player_rect: pygame.Rect, solids: list[pygame.Rect]):
        if not self._pending:
            return []
        out = self._pending
        self._pending = []
        return out

    def update(self, dt: float, player_rect: pygame.Rect, solids: list[pygame.Rect], bounds: pygame.Rect, enemies=None):
        if not self.alive:
            return
        if self.stun_timer > 0.0:
            self.stun_timer -= dt
            return

        # tick cooldowns
        self.burst_cd -= dt
        self.ring_cd -= dt
        self.dash_cd -= dt

        myc = _rect_center(self.rect)
        pc = _rect_center(player_rect)
        dist = myc.distance_to(pc)

        # --- State machine ---

        if self.state == "windup":
            self.state_t -= dt
            if self.state_t <= 0.0:
                self._start_dash()
            return

        if self.state == "dash":
            self.state_t -= dt
            vel = self.dash_dir * self.dash_speed
            before = pygame.Vector2(self.pos.x, self.pos.y)
            self._move_with_solids(vel * dt, solids, bounds)
            moved = self.pos.distance_to(before)

            # stop dash if blocked by wall
            if moved < 0.8:
                self.state_t = 0.0

            if self.state_t <= 0.0:
                self.state = "idle"
                self.state_t = 0.18
            return

        # --- Idle: choose next action ---

        self.state_t -= dt
        if self.state_t <= 0.0:
            has_los = _los(myc, pc, solids)

            # close range — prefer dash/ring
            if dist < 190 and self.dash_cd <= 0.0:
                self._start_windup(player_rect)
                return

            if has_los and self.burst_cd <= 0.0:
                self._shoot_burst(player_rect, solids)
                self.state_t = 0.35
            elif self.ring_cd <= 0.0:
                self._shoot_ring()
                self.state_t = 0.55
            elif self.dash_cd <= 0.0 and dist < 320:
                self._start_windup(player_rect)
                return
            else:
                self.state_t = 0.22

        # --- Movement: chase player, strafe if too close ---

        myc = _rect_center(self.rect)
        pc = _rect_center(player_rect)
        to_player = pc - myc
        if to_player.length_squared() > 0:
            to_player = to_player.normalize()
        else:
            to_player = pygame.Vector2(0, 0)

        move = pygame.Vector2(0, 0)
        if dist < 160:
            # back off and strafe
            move -= to_player
            strafe = pygame.Vector2(to_player.y, -to_player.x)
            if self._rng.random() < 0.5:
                strafe *= -1
            move += strafe * 0.55
        else:
            move += to_player * 0.8

        if move.length_squared() > 0:
            move = move.normalize()

        self.vel = move * self.speed
        self._move_with_solids(self.vel * dt, solids, bounds)

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return

        boss_color = getattr(settings, "BOSS_COLOR", (180, 60, 60))
        pygame.draw.rect(screen, boss_color, self.rect, border_radius=10)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, width=3, border_radius=10)

        # hp bar
        ratio = max(0.0, min(1.0, self.hp / max(1, self.hp_base)))
        x = self.rect.left
        y = self.rect.top - settings.HPBAR_H - 6
        w = self.rect.w
        h = settings.HPBAR_H
        pygame.draw.rect(screen, settings.HPBAR_BG, (x, y, w, h))
        pygame.draw.rect(screen, settings.HPBAR_FG, (x, y, int(w * ratio), h))

        # dash telegraph line
        if self.state == "windup" and self.windup_dir.length_squared() > 0:
            c = pygame.Vector2(self.rect.center)
            p2 = c + self.windup_dir.normalize() * 160
            pygame.draw.line(screen, (255, 220, 120), (int(c.x), int(c.y)), (int(p2.x), int(p2.y)), 4)