# actors/enemy.py
import math
import random
import os
import pygame
import settings
from heapq import heappush, heappop
from collections import deque

from core.sprite import SpriteVisual, AnimDef


# ------------------------------------------------------------
# Project root + enemy sprite path
# ------------------------------------------------------------
def _project_root() -> str:
    here = os.path.dirname(__file__)
    r1 = os.path.abspath(os.path.join(here, ".."))
    r2 = os.path.abspath(os.path.join(here, "..", ".."))
    return r2 if os.path.isdir(os.path.join(r2, "assets")) else r1


def _enemy_path(png_name: str) -> str:
    root = _project_root()
    return os.path.join(root, "assets", "sprites", "enemies", png_name)


# ------------------------------------------------------------
# Loose sheet: split by cols/rows using floor division
# (works even if image size is not divisible perfectly)
# ------------------------------------------------------------
class _LooseSheet:
    def __init__(self, path: str, cols: int, rows: int, *, scale: float = 1.0):
        self.path = str(path)
        self.cols = max(1, int(cols))
        self.rows = max(1, int(rows))
        self.scale = float(scale)

        surf = pygame.image.load(self.path).convert_alpha()
        w, h = surf.get_width(), surf.get_height()

        self.frame_w = max(1, w // self.cols)
        self.frame_h = max(1, h // self.rows)

        # build frames safely (never outside)
        self.frames: list[list[pygame.Surface]] = []
        for ry in range(self.rows):
            row_frames: list[pygame.Surface] = []
            for cx in range(self.cols):
                x = cx * self.frame_w
                y = ry * self.frame_h
                # clamp size to surface bounds
                fw = min(self.frame_w, w - x)
                fh = min(self.frame_h, h - y)
                if fw <= 0 or fh <= 0:
                    # fallback 1x1 transparent
                    f = pygame.Surface((1, 1), pygame.SRCALPHA)
                else:
                    r = pygame.Rect(x, y, fw, fh)
                    f = surf.subsurface(r).copy()
                if self.scale != 1.0:
                    f = pygame.transform.scale(
                        f,
                        (int(round(f.get_width() * self.scale)), int(round(f.get_height() * self.scale))),
                    )
                row_frames.append(f)
            self.frames.append(row_frames)

    def get(self, row: int, col: int) -> pygame.Surface:
        r = max(0, min(self.rows - 1, int(row)))
        c = max(0, min(self.cols - 1, int(col)))
        return self.frames[r][c]


def _make_enemy_visual_loose(png: str, cols: int, rows: int, anims: dict[str, AnimDef], default: str) -> SpriteVisual | None:
    try:
        scale = float(getattr(settings, "SPRITE_SCALE", 2.0))
        offy = int(getattr(settings, "SPRITE_OFFSET_Y", 6))
        sheet = _LooseSheet(_enemy_path(png), cols, rows, scale=scale)
        return SpriteVisual(sheet, anims, default=default, anchor="midbottom", offset=(0, offy))
    except Exception as e:
        print("[ENEMY SPRITE LOAD FAIL]", png, e)
        return None


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _clamp(v, a, b):
    return a if v < a else b if v > b else v


def _rect_center(r: pygame.Rect) -> pygame.Vector2:
    return pygame.Vector2(r.centerx, r.centery)


def _los(a: pygame.Vector2, b: pygame.Vector2, solids: list[pygame.Rect]) -> bool:
    v = b - a
    dist = v.length()
    if dist <= 1.0:
        return True
    step = max(1.0, float(settings.AI_LOS_STEP))
    dirv = v / dist
    p = pygame.Vector2(a.x, a.y)
    n = int(dist // step)
    for _ in range(n):
        p += dirv * step
        if any(s.collidepoint(int(p.x), int(p.y)) for s in solids):
            return False
    return True


# ------------------------------------------------------------
# Bullet
# ------------------------------------------------------------
class EnemyBullet:
    def __init__(self, pos: pygame.Vector2, vel: pygame.Vector2, damage: int):
        self.pos = pygame.Vector2(pos.x, pos.y)
        self.vel = pygame.Vector2(vel.x, vel.y)
        self.damage = int(damage)
        s = settings.ENEMY_BULLET_SIZE
        self.rect = pygame.Rect(int(pos.x - s / 2), int(pos.y - s / 2), s, s)
        self.ttl = float(settings.ENEMY_BULLET_TTL)
        self.alive = True

    def update(self, dt: float, solids: list[pygame.Rect], bounds: pygame.Rect):
        if not self.alive:
            return
        self.ttl -= dt
        if self.ttl <= 0:
            self.alive = False
            return

        self.pos += self.vel * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        if not bounds.collidepoint(self.rect.center):
            self.alive = False
            return

        if any(self.rect.colliderect(s) for s in solids):
            self.alive = False

    def draw(self, screen: pygame.Surface):
        if self.alive:
            pygame.draw.rect(screen, settings.ENEMY_BULLET_COLOR, self.rect)


# ------------------------------------------------------------
# A*
# ------------------------------------------------------------
class _AStarGrid:
    def __init__(self, bounds: pygame.Rect, solids: list[pygame.Rect], cell: int, agent_radius: int):
        self.bounds = bounds
        self.cell = max(16, int(cell))
        self.cols = max(1, bounds.w // self.cell)
        self.rows = max(1, bounds.h // self.cell)

        pad = max(2, int(agent_radius) + 2)
        self._inflated_solids = [s.inflate(pad * 2, pad * 2) for s in solids]

        self.blocked = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        for gy in range(self.rows):
            for gx in range(self.cols):
                c = self.cell_to_pos(gx, gy)
                if any(s.collidepoint(int(c.x), int(c.y)) for s in self._inflated_solids):
                    self.blocked[gy][gx] = True

    def pos_to_cell(self, pos: pygame.Vector2) -> tuple[int, int]:
        gx = int((pos.x - self.bounds.left) // self.cell)
        gy = int((pos.y - self.bounds.top) // self.cell)
        gx = _clamp(gx, 0, self.cols - 1)
        gy = _clamp(gy, 0, self.rows - 1)
        return gx, gy

    def cell_to_pos(self, gx: int, gy: int) -> pygame.Vector2:
        x = self.bounds.left + gx * self.cell + self.cell * 0.5
        y = self.bounds.top + gy * self.cell + self.cell * 0.5
        return pygame.Vector2(x, y)

    def is_walkable(self, gx: int, gy: int) -> bool:
        if gx < 0 or gy < 0 or gx >= self.cols or gy >= self.rows:
            return False
        return not self.blocked[gy][gx]

    def _nearest_walkable(self, start: tuple[int, int], max_r: int = 6) -> tuple[int, int] | None:
        if self.is_walkable(start[0], start[1]):
            return start

        q = deque([start])
        seen = {start}
        while q:
            cx, cy = q.popleft()
            if self.is_walkable(cx, cy):
                return (cx, cy)

            if max(abs(cx - start[0]), abs(cy - start[1])) >= max_r:
                continue

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
                nx, ny = cx + dx, cy + dy
                p = (nx, ny)
                if p in seen:
                    continue
                if 0 <= nx < self.cols and 0 <= ny < self.rows:
                    seen.add(p)
                    q.append(p)
        return None

    def neighbors(self, gx: int, gy: int):
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]
        for dx, dy in dirs:
            nx, ny = gx + dx, gy + dy
            if not self.is_walkable(nx, ny):
                continue
            if dx != 0 and dy != 0:
                if not self.is_walkable(gx + dx, gy) or not self.is_walkable(gx, gy + dy):
                    continue
                cost = 1.4142
            else:
                cost = 1.0
            yield nx, ny, cost

    def heuristic(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return (dx + dy) + (1.4142 - 2.0) * min(dx, dy)

    def astar(self, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
        if start == goal:
            return [start]

        g2 = self._nearest_walkable(goal, max_r=7)
        if g2 is None:
            return []
        goal = g2

        openh = []
        heappush(openh, (0.0, start))
        came: dict[tuple[int, int], tuple[int, int]] = {}
        gscore = {start: 0.0}

        while openh:
            _, cur = heappop(openh)
            if cur == goal:
                path = [cur]
                while cur in came:
                    cur = came[cur]
                    path.append(cur)
                path.reverse()
                return path

            for nx, ny, cost in self.neighbors(cur[0], cur[1]):
                nxt = (nx, ny)
                ng = gscore[cur] + cost
                if nxt not in gscore or ng < gscore[nxt]:
                    gscore[nxt] = ng
                    came[nxt] = cur
                    f = ng + self.heuristic(nxt, goal)
                    heappush(openh, (f, nxt))

        return []


# ------------------------------------------------------------
# Base
# ------------------------------------------------------------
class EnemyBase:
    def __init__(self, x: float, y: float):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)

        s = settings.ENEMY_SIZE
        self.rect = pygame.Rect(int(x - s / 2), int(y - s / 2), s, s)

        self.visual: SpriteVisual | None = None
        self.anim_state = "base"

        self.hp = int(settings.ENEMY_HP)
        self.max_hp = int(self.hp)
        self.alive = True

        self.speed = float(getattr(settings, "ENEMY_SPEED", 140.0))

        self._hit_swing_ids: set[int] = set()
        self.stun_timer = 0.0

        self.contact_damage = int(getattr(settings, "ENEMY_CONTACT_DAMAGE", 0))
        self.contact_cd = float(getattr(settings, "ENEMY_CONTACT_CD", 0.55))
        self._contact_timer = 0.0

        self.knock_vel = pygame.Vector2(0, 0)
        self.knock_time = 0.0

        self.status_effects = []

    def add_status(self, status):
        self.status_effects.append(status)

    def _update_statuses(self, dt: float):
        new_status = []
        for s in self.status_effects:
            s.update(dt, self)
            if getattr(s, "alive", False):
                new_status.append(s)
        self.status_effects = new_status

    def _update_visual(self, dt: float):
        if self.visual is None:
            return
        self.visual.set_state(str(self.anim_state))
        self.visual.update(dt)

    def draw_hp_bar(self, screen: pygame.Surface, max_hp: int | None = None):
        if not self.alive:
            return
        mhp = int(max_hp) if isinstance(max_hp, (int, float)) else int(getattr(self, "max_hp", settings.ENEMY_HP))
        if mhp <= 0:
            return
        ratio = max(0.0, min(1.0, self.hp / mhp))
        x = self.rect.left
        y = self.rect.top - settings.HPBAR_H - 2
        w = self.rect.w
        h = settings.HPBAR_H
        pygame.draw.rect(screen, settings.HPBAR_BG, (x, y, w, h))
        pygame.draw.rect(screen, settings.HPBAR_FG, (x, y, int(w * ratio), h))

    def can_deal_contact_now(self) -> bool:
        return self._contact_timer <= 0.0

    def mark_contact_dealt(self):
        self._contact_timer = self.contact_cd

    def apply_knockback(self, dirv: pygame.Vector2, strength: float, time_s: float):
        if not self.alive:
            return
        if dirv.length_squared() == 0:
            return
        self.knock_vel = dirv.normalize() * float(strength)
        self.knock_time = max(self.knock_time, float(time_s))

    def apply_stun(self, t: float):
        self.stun_timer = max(self.stun_timer, float(t))

    def take_projectile_hit(self, dmg: int):
        if not self.alive:
            return
        self.hp -= int(dmg)
        if self.hp <= 0:
            self.alive = False

    def take_blast_hit(self, dmg: int, blast_id: int):
        self.take_projectile_hit(dmg)

    def take_melee_hit(self, dmg: int, swing_id: int):
        if swing_id in self._hit_swing_ids:
            return
        self._hit_swing_ids.add(swing_id)
        self.take_projectile_hit(dmg)

    def _move_with_solids(self, delta: pygame.Vector2, solids: list[pygame.Rect], bounds: pygame.Rect):
        self.pos.x += delta.x
        self.rect.centerx = int(self.pos.x)
        for r in solids:
            if self.rect.colliderect(r):
                if delta.x > 0:
                    self.rect.right = r.left
                elif delta.x < 0:
                    self.rect.left = r.right
                self.pos.x = self.rect.centerx

        self.pos.y += delta.y
        self.rect.centery = int(self.pos.y)
        for r in solids:
            if self.rect.colliderect(r):
                if delta.y > 0:
                    self.rect.bottom = r.top
                elif delta.y < 0:
                    self.rect.top = r.bottom
                self.pos.y = self.rect.centery

        if self.rect.left < bounds.left:
            self.rect.left = bounds.left
        if self.rect.right > bounds.right:
            self.rect.right = bounds.right
        if self.rect.top < bounds.top:
            self.rect.top = bounds.top
        if self.rect.bottom > bounds.bottom:
            self.rect.bottom = bounds.bottom

        self.pos.x = float(self.rect.centerx)
        self.pos.y = float(self.rect.centery)

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return
        if self.visual is not None:
            self.visual.draw(screen, self.rect)
        else:
            pygame.draw.rect(screen, (200, 70, 70), self.rect)
        self.draw_hp_bar(screen)


# ------------------------------------------------------------
# Chaser: файл 68x64 -> split 2x2 -> кадр 34x32
# Используем 3 направления: down/up/side
# (side берём из (row=1,col=0), flip_x для лево/право)
# ------------------------------------------------------------
class EnemyChaser(EnemyBase):
    def __init__(self, x: float, y: float):
        super().__init__(x, y)

        anims = {
            "down": AnimDef(row=1, col=1, frames=1, fps=1),
            "up":   AnimDef(row=0, col=1, frames=1, fps=1),
            "side": AnimDef(row=1, col=0, frames=1, fps=1),
        }
        self.visual = _make_enemy_visual_loose("chaser.png", cols=2, rows=2, anims=anims, default="down")
        self.anim_state = "down"
        if self.visual is not None:
            self.visual.flip_x = False

        self._repath = 0.0
        self._path: list[pygame.Vector2] = []
        self._path_i = 0
        self._last_player_pos = pygame.Vector2(-99999, -99999)

        self._stuck_timer = 0.0
        self._stuck_ref = pygame.Vector2(self.pos.x, self.pos.y)

        self._escape_timer = 0.0
        self._escape_dir = pygame.Vector2(0, 0)

        self._rng = random.Random(int(x * 1000) ^ (int(y * 1000) << 1))

    def _separation(self, enemies: list["EnemyBase"]) -> pygame.Vector2:
        force = pygame.Vector2(0, 0)
        myc = _rect_center(self.rect)
        r = float(settings.AI_SEPARATION_RADIUS)
        r2 = r * r
        for e in enemies:
            if e is self or not e.alive:
                continue
            dc = myc - _rect_center(e.rect)
            d2 = dc.length_squared()
            if 0 < d2 < r2:
                d = math.sqrt(d2)
                strength = (r - d) / r
                force += (dc / max(d, 1e-6)) * strength
        if force.length_squared() > 0:
            force = force.normalize() * float(settings.AI_SEPARATION_FORCE)
        return force

    def _smooth_path(self, pts: list[pygame.Vector2], solids: list[pygame.Rect]) -> list[pygame.Vector2]:
        if len(pts) <= 2:
            return pts
        out = [pts[0]]
        i = 0
        while i < len(pts) - 1:
            k = len(pts) - 1
            while k > i + 1:
                if _los(pts[i], pts[k], solids):
                    break
                k -= 1
            out.append(pts[k])
            i = k
        return out

    def _build_path(self, player_rect: pygame.Rect, solids: list[pygame.Rect], bounds: pygame.Rect):
        agent_radius = self.rect.w // 2
        grid = _AStarGrid(bounds, solids, settings.AI_GRID, agent_radius)

        start = grid.pos_to_cell(_rect_center(self.rect))
        goal = grid.pos_to_cell(_rect_center(player_rect))

        cells = grid.astar(start, goal)
        if not cells:
            self._path = []
            self._path_i = 0
            return

        pts = [grid.cell_to_pos(gx, gy) for (gx, gy) in cells]
        pts = self._smooth_path(pts, solids)

        while len(pts) > 1 and pts[0].distance_to(_rect_center(self.rect)) < settings.AI_GRID * 0.7:
            pts.pop(0)

        self._path = pts
        self._path_i = 0

    def _face_to_player(self, player_rect: pygame.Rect):
        if self.visual is None:
            return
        myc = _rect_center(self.rect)
        pc = _rect_center(player_rect)
        d = pc - myc
        if d.length_squared() == 0:
            d = pygame.Vector2(0, 1)

        if abs(d.x) > abs(d.y):
            self.anim_state = "side"
            self.visual.flip_x = (d.x < 0)
        else:
            self.anim_state = "up" if d.y < 0 else "down"

    def update(self, dt: float, player_rect: pygame.Rect, solids: list[pygame.Rect], bounds: pygame.Rect, enemies=None):
        if not self.alive:
            return

        self._update_statuses(dt)

        if self.stun_timer > 0.0:
            self.stun_timer -= dt
            self.vel.update(0, 0)
            self._face_to_player(player_rect)
            self._update_visual(dt)
            return

        if self.knock_time > 0.0:
            self.knock_time -= dt
            self._move_with_solids(self.knock_vel * dt, solids, bounds)
            self.vel = pygame.Vector2(self.knock_vel.x, self.knock_vel.y)
            self._face_to_player(player_rect)
            self._update_visual(dt)
            return

        if self._contact_timer > 0.0:
            self._contact_timer -= dt

        myc = _rect_center(self.rect)
        player_pos = _rect_center(player_rect)

        if self._escape_timer > 0.0:
            self._escape_timer -= dt
            self.vel = self._escape_dir * float(self.speed)
            self._move_with_solids(self.vel * dt, solids, bounds)
            self._face_to_player(player_rect)
            self._update_visual(dt)
            return

        direct = _los(myc, player_pos, solids) and myc.distance_to(player_pos) <= settings.AI_DIRECT_CHASE_DIST

        self._repath -= dt
        if (not direct) and (
            self._repath <= 0.0
            or player_pos.distance_to(self._last_player_pos) > settings.AI_REPATH_PLAYER_DIST
            or self._path_i >= len(self._path)
        ):
            self._build_path(player_rect, solids, bounds)
            self._repath = settings.AI_REPATH_TIME
            self._last_player_pos = player_pos

        target = player_pos
        if (not direct) and self._path and self._path_i < len(self._path):
            target = self._path[self._path_i]
            if myc.distance_to(target) < max(12.0, settings.AI_GRID * 0.55):
                self._path_i += 1

        dirv = (target - myc)
        if dirv.length_squared() > 0:
            dirv = dirv.normalize()
        else:
            dirv = pygame.Vector2(0, 0)

        sep = pygame.Vector2(0, 0)
        if enemies:
            sep = self._separation(enemies)

        move_dir = dirv + (sep / max(1.0, float(settings.AI_SEPARATION_FORCE)))
        if move_dir.length_squared() > 0:
            move_dir = move_dir.normalize()

        self.vel = move_dir * float(self.speed)

        before = pygame.Vector2(self.pos.x, self.pos.y)
        self._move_with_solids(self.vel * dt, solids, bounds)
        moved = self.pos.distance_to(before)

        self._stuck_timer += dt
        if self._stuck_timer >= settings.AI_STUCK_TIME:
            self._stuck_timer = 0.0
            moved2 = self.pos.distance_to(self._stuck_ref)
            self._stuck_ref = pygame.Vector2(self.pos.x, self.pos.y)
            if moved2 < settings.AI_STUCK_MIN_MOVE:
                moved = 0.0

        if moved < 0.8:
            slide = pygame.Vector2(dirv.y, -dirv.x)
            if self._rng.random() < 0.5:
                slide *= -1
            if slide.length_squared() > 0:
                self._escape_dir = slide.normalize()
                self._escape_timer = 0.18
                self._repath = 0.0

        self._face_to_player(player_rect)
        self._update_visual(dt)


# ------------------------------------------------------------
# Shooter: файл 27x61 -> split 1x2 -> кадр 27x30
# base (row0), attack (row1)
# ------------------------------------------------------------
class EnemyShooter(EnemyChaser):
    def __init__(self, x: float, y: float):
        super().__init__(x, y)

        anims = {
            "base":   AnimDef(row=0, col=0, frames=1, fps=1),
            "attack": AnimDef(row=1, col=0, frames=1, fps=1),
        }
        self.visual = _make_enemy_visual_loose("shooter.png", cols=1, rows=2, anims=anims, default="base")
        self.anim_state = "base"

        self.shoot_cd = self._rng.uniform(0.15, 0.55)
        self._pending_shot = False
        self._attack_vis_t = 0.0

    def update(self, dt: float, player_rect: pygame.Rect, solids: list[pygame.Rect], bounds: pygame.Rect, enemies=None):
        super().update(dt, player_rect, solids, bounds, enemies=enemies)

        if not self.alive:
            return
        if self.stun_timer > 0.0 or self.knock_time > 0.0:
            return

        myc = _rect_center(self.rect)
        pc = _rect_center(player_rect)
        has_los = _los(myc, pc, solids)
        dist = myc.distance_to(pc)

        self.shoot_cd -= dt
        if self.shoot_cd <= 0.0 and has_los and dist <= settings.AI_SHOOT_RANGE:
            self.shoot_cd = float(settings.AI_SHOOT_COOLDOWN)
            self._pending_shot = True
        else:
            self._pending_shot = False

        if self._attack_vis_t > 0.0:
            self._attack_vis_t = max(0.0, self._attack_vis_t - dt)
            self.anim_state = "attack"
        else:
            self.anim_state = "base"

        self._update_visual(dt)

    def pop_shot(self, player_rect: pygame.Rect, solids: list[pygame.Rect]) -> EnemyBullet | None:
        if not self._pending_shot:
            return None
        myc = _rect_center(self.rect)
        pc = _rect_center(player_rect)
        if not _los(myc, pc, solids):
            return None
        v = pc - myc
        if v.length_squared() == 0:
            return None

        self._attack_vis_t = 0.12
        v = v.normalize() * float(settings.ENEMY_BULLET_SPEED)
        return EnemyBullet(myc, v, settings.ENEMY_BULLET_DAMAGE)


# ------------------------------------------------------------
# Turret: файл 94x43 -> split 3x1 -> кадр 31x43
# base/shoot/cd = col 0/1/2
# ------------------------------------------------------------
class EnemyTurret(EnemyBase):
    def __init__(self, x: float, y: float):
        super().__init__(x, y)

        anims = {
            "base":  AnimDef(row=0, col=0, frames=1, fps=1),
            "shoot": AnimDef(row=0, col=1, frames=1, fps=1),
            "cd":    AnimDef(row=0, col=2, frames=1, fps=1),
        }
        self.visual = _make_enemy_visual_loose("turret.png", cols=3, rows=1, anims=anims, default="base")
        self.anim_state = "base"

        self.shoot_cd = 0.6
        self._pending_shot = False
        self._shoot_vis_t = 0.0
        self._cd_vis_t = 0.0

    def update(self, dt: float, player_rect: pygame.Rect, solids: list[pygame.Rect], bounds: pygame.Rect, enemies=None):
        if not self.alive:
            return

        self._update_statuses(dt)

        if self.stun_timer > 0.0:
            self.stun_timer -= dt
            self.vel.update(0, 0)
            self.anim_state = "base"
            self._update_visual(dt)
            return

        if self.knock_time > 0.0:
            self.knock_time -= dt
            self._move_with_solids(self.knock_vel * dt, solids, bounds)
            self.vel = pygame.Vector2(self.knock_vel.x, self.knock_vel.y)
            self.anim_state = "base"
            self._update_visual(dt)
            return

        if self._contact_timer > 0.0:
            self._contact_timer -= dt

        if self._shoot_vis_t > 0.0:
            self._shoot_vis_t = max(0.0, self._shoot_vis_t - dt)
        if self._cd_vis_t > 0.0:
            self._cd_vis_t = max(0.0, self._cd_vis_t - dt)

        self.shoot_cd -= dt
        myc = _rect_center(self.rect)
        pc = _rect_center(player_rect)

        if self.shoot_cd <= 0.0 and _los(myc, pc, solids) and myc.distance_to(pc) <= settings.AI_SHOOT_RANGE:
            self.shoot_cd = float(settings.AI_SHOOT_COOLDOWN)
            self._pending_shot = True
        else:
            self._pending_shot = False

        if self._shoot_vis_t > 0.0:
            self.anim_state = "shoot"
        elif self._cd_vis_t > 0.0:
            self.anim_state = "cd"
        else:
            self.anim_state = "base"

        self.vel.update(0, 0)
        self._update_visual(dt)

    def pop_shot(self, player_rect: pygame.Rect, solids: list[pygame.Rect]) -> EnemyBullet | None:
        if not self._pending_shot:
            return None

        myc = _rect_center(self.rect)
        pc = _rect_center(player_rect)
        if not _los(myc, pc, solids):
            return None

        v = pc - myc
        if v.length_squared() == 0:
            return None

        self._shoot_vis_t = 0.10
        self._cd_vis_t = 0.25

        v = v.normalize() * float(settings.ENEMY_BULLET_SPEED)
        return EnemyBullet(myc, v, settings.ENEMY_BULLET_DAMAGE)


# ------------------------------------------------------------
# Остальные классы оставь как у тебя (tank/dasher/summoner),
# потому что ошибки сейчас только по chaser/shooter/turret.
# ------------------------------------------------------------
class EnemyTank(EnemyChaser):
    def __init__(self, x: float, y: float):
        super().__init__(x, y)
        s = int(settings.TANK_SIZE)
        self.rect = pygame.Rect(int(x - s / 2), int(y - s / 2), s, s)
        self.pos = pygame.Vector2(self.rect.centerx, self.rect.centery)
        self.hp = int(settings.TANK_HP)
        self.max_hp = int(self.hp)
        self.contact_damage = int(settings.TANK_CONTACT_DAMAGE)
        self.speed = float(settings.TANK_SPEED)

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return
        if self.visual is not None:
            self.visual.draw(screen, self.rect)
        else:
            pygame.draw.rect(screen, settings.TANK_COLOR, self.rect)
            pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
        self.draw_hp_bar(screen)


class EnemyDasher(EnemyBase):
    def __init__(self, x: float, y: float):
        super().__init__(x, y)

        s = int(settings.DASHER_SIZE)
        self.rect = pygame.Rect(int(x - s / 2), int(y - s / 2), s, s)
        self.pos = pygame.Vector2(self.rect.centerx, self.rect.centery)
        self.hp = int(settings.DASHER_HP)
        self.max_hp = int(self.hp)

        self.base_speed = float(settings.DASHER_SPEED)
        self.windup = float(settings.DASHER_WINDUP)
        self.dash_time = float(settings.DASHER_DASH_TIME)
        self.dash_speed = float(settings.DASHER_DASH_SPEED)
        self.cd = float(settings.DASHER_CD)

        self.state = "idle"  # idle / windup / dash
        self.t = 0.25
        self.dir = pygame.Vector2(0, 1)

        # dasher.png: 144x96 => cols=3 rows=3 => frame 48x32
        # row0: walk (3 frames)
        # row1: dash frames (first 2), + prep (3rd frame)
        anims = {
            "walk":   AnimDef(row=0, col=0, frames=3, fps=10, loop=True),
            "dash":   AnimDef(row=1, col=0, frames=2, fps=16, loop=False),
            "windup": AnimDef(row=1, col=2, frames=1, fps=1, loop=False),
        }
        self.visual = _make_enemy_visual_loose("dasher.png", cols=3, rows=3, anims=anims, default="walk")
        self.anim_state = "walk"

    def update(self, dt: float, player_rect: pygame.Rect, solids: list[pygame.Rect], bounds: pygame.Rect, enemies=None):
        if not self.alive:
            return

        self._update_statuses(dt)

        if self.stun_timer > 0.0:
            self.stun_timer -= dt
            self.vel.update(0, 0)
            self.anim_state = "walk"
            self._update_visual(dt)
            return

        if self.knock_time > 0.0:
            self.knock_time -= dt
            self._move_with_solids(self.knock_vel * dt, solids, bounds)
            self.vel = pygame.Vector2(self.knock_vel.x, self.knock_vel.y)
            self.anim_state = "walk"
            self._update_visual(dt)
            return

        if self._contact_timer > 0.0:
            self._contact_timer -= dt

        self.cd -= dt
        myc = _rect_center(self.rect)
        pc = _rect_center(player_rect)

        if self.state == "windup":
            self.t -= dt
            self.vel.update(0, 0)
            self.anim_state = "windup"
            if self.t <= 0.0:
                self.state = "dash"
                self.t = self.dash_time
            self._update_visual(dt)
            return

        if self.state == "dash":
            self.t -= dt
            vel = self.dir * self.dash_speed
            self.vel = pygame.Vector2(vel.x, vel.y)
            self._move_with_solids(vel * dt, solids, bounds)
            self.anim_state = "dash"
            if self.t <= 0.0:
                self.state = "idle"
                self.t = 0.25
                self.cd = float(settings.DASHER_CD)
            self._update_visual(dt)
            return

        # idle/move
        if self.cd <= 0.0 and myc.distance_to(pc) < 320:
            d = pc - myc
            if d.length_squared() == 0:
                d = pygame.Vector2(0, 1)
            self.dir = d.normalize()
            self.state = "windup"
            self.t = self.windup
            self.vel.update(0, 0)
            self.anim_state = "windup"
            self._update_visual(dt)
            return

        d = pc - myc
        if d.length_squared() > 0:
            d = d.normalize()
        self.vel = d * self.base_speed
        self._move_with_solids(self.vel * dt, solids, bounds)

        self.anim_state = "walk"
        self._update_visual(dt)


class EnemySummoner(EnemyBase):
    def __init__(self, x: float, y: float):
        super().__init__(x, y)
        s = int(settings.SUMMONER_SIZE)
        self.rect = pygame.Rect(int(x - s / 2), int(y - s / 2), s, s)
        self.pos = pygame.Vector2(self.rect.centerx, self.rect.centery)
        self.hp = int(settings.SUMMONER_HP)
        self.max_hp = int(self.hp)

        self.speed = float(settings.SUMMONER_SPEED)
        self.cd = float(settings.SUMMONER_SUMMON_CD)

        self._pending_spawns = []
        self._rng = random.Random((int(x) << 16) ^ int(y) ^ 911)
        self._owner_id = id(self)

    def pop_spawns(self):
        if not self._pending_spawns:
            return []
        out = self._pending_spawns
        self._pending_spawns = []
        return out

    def _count_my_minions(self, enemies) -> int:
        if not enemies:
            return 0
        c = 0
        for e in enemies:
            if e is self:
                continue
            if not getattr(e, "alive", True):
                continue
            if getattr(e, "minion_owner_id", None) == self._owner_id:
                c += 1
        return c

    def update(self, dt: float, player_rect: pygame.Rect, solids: list[pygame.Rect], bounds: pygame.Rect, enemies=None):
        if not self.alive:
            return

        self._update_statuses(dt)

        if self.stun_timer > 0.0:
            self.stun_timer -= dt
            return

        if self.knock_time > 0.0:
            self.knock_time -= dt
            self._move_with_solids(self.knock_vel * dt, solids, bounds)
            return

        if self._contact_timer > 0.0:
            self._contact_timer -= dt

        self.cd -= dt
        myc = _rect_center(self.rect)
        pc = _rect_center(player_rect)
        dist = myc.distance_to(pc)

        d = pc - myc
        if d.length_squared() > 0:
            d = d.normalize()

        move = pygame.Vector2(0, 0)
        if dist < 220:
            move -= d
        elif dist > 360:
            move += d * 0.6

        if move.length_squared() > 0:
            move = move.normalize()
        self.vel = move * self.speed
        self._move_with_solids(self.vel * dt, solids, bounds)

        if self.cd <= 0.0:
            max_m = int(settings.SUMMONER_MAX_MINIONS)
            alive_my_minions = self._count_my_minions(enemies)
            if alive_my_minions < max_m:
                ang = self._rng.random() * 2.0 * math.pi
                p = myc + pygame.Vector2(math.cos(ang), math.sin(ang)) * 70
                p.x = max(bounds.left + 60, min(bounds.right - 60, p.x))
                p.y = max(bounds.top + 60, min(bounds.bottom - 60, p.y))

                e = EnemyChaser(p.x, p.y)
                e.minion_owner_id = self._owner_id
                e.is_minion = True

                if not any(e.rect.colliderect(s) for s in solids):
                    self._pending_spawns.append(e)

            self.cd = float(settings.SUMMONER_SUMMON_CD)

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return
        pygame.draw.rect(screen, settings.SUMMONER_COLOR, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
        self.draw_hp_bar(screen)