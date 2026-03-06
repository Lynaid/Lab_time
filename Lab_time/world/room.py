# world/room.py
import os
import random
import pygame
import settings

from actors.enemy import (
    EnemyChaser, EnemyShooter, EnemyTurret, EnemyBullet,
    EnemyTank, EnemyDasher, EnemySummoner
)
from actors.boss import BossPhase1

from world.objects import Rock, Crate, Spikes, MapObject
from world.pickups import Pickup

from world.layouts import (
    LAYOUTS_NORMAL,
    LAYOUTS_BOSS,
    LAYOUTS_SECRET,
    LAYOUTS_SHOP,
    LAYOUTS_TREASURE,
)

TILE = int(getattr(settings, "TILE_SIZE", 32))
ROOM_SPR_DIR = os.path.join("assets", "sprites", "room")

#  467x315
DEFAULT_FLOOR_RECT_LOCAL = pygame.Rect(23, 23, 421, 266)


def _mask_outside_rect(surf: pygame.Surface, keep_rect: pygame.Rect) -> pygame.Surface:
    out = surf.copy()
    w, h = out.get_size()
    if keep_rect.top > 0:
        out.fill((0, 0, 0, 0), pygame.Rect(0, 0, w, keep_rect.top))
    if keep_rect.bottom < h:
        out.fill((0, 0, 0, 0), pygame.Rect(0, keep_rect.bottom, w, h - keep_rect.bottom))
    if keep_rect.left > 0:
        out.fill((0, 0, 0, 0), pygame.Rect(0, keep_rect.top, keep_rect.left, keep_rect.height))
    if keep_rect.right < w:
        out.fill((0, 0, 0, 0), pygame.Rect(keep_rect.right, keep_rect.top, w - keep_rect.right, keep_rect.height))
    return out


def _mask_inside_rect(surf: pygame.Surface, cut_rect: pygame.Rect) -> pygame.Surface:
    out = surf.copy()
    out.fill((0, 0, 0, 0), cut_rect)
    return out


def _project_root() -> str:
    here = os.path.dirname(__file__)
    r1 = os.path.abspath(os.path.join(here, ".."))
    r2 = os.path.abspath(os.path.join(here, "..", ".."))
    return r2 if os.path.isdir(os.path.join(r2, "assets")) else r1


def _extract_alpha_components_with_rects(
    sheet: pygame.Surface, *, min_area: int = 30
) -> list[tuple[pygame.Rect, pygame.Surface]]:
    """
    Вырезает отдельные спрайты из атласа по непрозрачным регионам.
    БЕЗ numpy: через pygame.mask.
    Возвращает (rect_on_sheet, surface).
    """
    m = pygame.mask.from_surface(sheet, 1)
    rects = m.get_bounding_rects()
    if not rects:
        return []

    out: list[tuple[pygame.Rect, pygame.Surface]] = []
    for r in rects:
        if r.w <= 1 or r.h <= 1:
            continue
        if (r.w * r.h) < min_area:
            continue
        out.append((r, sheet.subsurface(r).copy()))
    return out


class _RoomArt:
    """
    Ассеты:
      - room_floor.png: только пол (остальное прозрачно)
      - room_walls.png: стены/серое вне зоны (пол прозрачен)
      - fallback: room_tiles.png (если split-версий нет)

      - Doors.png: 2 спрайта (closed/open)
      - Rocks.png: сверху серый, снизу коричневый (2 спрайта)
      - Detail.png: атлас декора (альфа-нарезка)
    """
    def __init__(self):
        self.ok = False

        # background parts (split)
        self.room_floor: pygame.Surface | None = None
        self.room_walls: pygame.Surface | None = None

        # optional fallback
        self.room_full_fallback: pygame.Surface | None = None

        # ref background for rect conversion (MUST match scaled draw size ratios)
        self.room_bg: pygame.Surface | None = None

        self.door_closed: pygame.Surface | None = None
        self.door_open: pygame.Surface | None = None

        self.rock_gray: pygame.Surface | None = None
        self.rock_brown: pygame.Surface | None = None

        self.detail_sprites: list[pygame.Surface] = []

        root = _project_root()
        try:
            base_dir = os.path.join(root, ROOM_SPR_DIR)

            # split background
            floor_path = os.path.join(base_dir, "room_floor.png")
            walls_path = os.path.join(base_dir, "room_walls.png")

            if os.path.isfile(floor_path):
                self.room_floor = pygame.image.load(floor_path).convert_alpha()
            else:
                self.room_floor = None

            if os.path.isfile(walls_path):
                self.room_walls = pygame.image.load(walls_path).convert_alpha()
            else:
                self.room_walls = None

            # fallback single image
            full_path = os.path.join(base_dir, "room_tiles.png")
            if os.path.isfile(full_path):
                self.room_full_fallback = pygame.image.load(full_path).convert_alpha()

            self.room_bg = self.room_walls or self.room_floor or self.room_full_fallback

            # Doors
            doors_path = os.path.join(base_dir, "Doors.png")
            if os.path.isfile(doors_path):
                doors_sheet = pygame.image.load(doors_path).convert_alpha()
                parts = _extract_alpha_components_with_rects(doors_sheet, min_area=20)
                parts.sort(key=lambda t: (t[0].left, t[0].top))
                if len(parts) >= 1:
                    self.door_closed = parts[0][1]
                if len(parts) >= 2:
                    self.door_open = parts[1][1]

            # Rocks
            rocks_path = os.path.join(base_dir, "Rocks.png")
            if os.path.isfile(rocks_path):
                rocks_sheet = pygame.image.load(rocks_path).convert_alpha()
                parts = _extract_alpha_components_with_rects(rocks_sheet, min_area=20)
                parts.sort(key=lambda t: (t[0].top, t[0].left))
                if len(parts) >= 1:
                    self.rock_gray = parts[0][1]
                if len(parts) >= 2:
                    self.rock_brown = parts[1][1]

            # Detail
            detail_path = os.path.join(base_dir, "Detail.png")
            if os.path.isfile(detail_path):
                detail_sheet = pygame.image.load(detail_path).convert_alpha()
                parts = _extract_alpha_components_with_rects(detail_sheet, min_area=25)
                parts.sort(key=lambda t: (t[0].top, t[0].left))
                self.detail_sprites = [s for _, s in parts]

            self.ok = True
        except Exception as e:
            print("[ROOM ART LOAD FAIL]", e)
            self.ok = False


_ROOM_ART: _RoomArt | None = None


def _room_art() -> _RoomArt:
    global _ROOM_ART
    if _ROOM_ART is None:
        _ROOM_ART = _RoomArt()
    return _ROOM_ART


class Room:
    STATE_IDLE = "idle"
    STATE_COMBAT = "combat"
    STATE_CLEARED = "cleared"

    def __init__(
        self,
        cell: int,
        bounds: pygame.Rect,
        room_type: str,
        floor_seed: int | None = None,
        difficulty=1.0,
        **kwargs
    ):
        self.cell = int(cell)
        self.bounds = bounds
        self.room_type = str(room_type)
        self.floor_seed = floor_seed

        self.difficulty = {}
        self.difficulty_scale = 1.0
        if isinstance(difficulty, dict):
            self.difficulty = difficulty
            for k in ("scale", "mult", "difficulty", "level", "enemy_mult"):
                if k in difficulty and isinstance(difficulty[k], (int, float)):
                    self.difficulty_scale = float(difficulty[k])
                    break
        elif isinstance(difficulty, (int, float)):
            self.difficulty_scale = float(difficulty)

        self.objects: list[MapObject] = []
        self.solids: list[pygame.Rect] = []

        # walls + cached floor rect
        self.wall_rects: list[pygame.Rect] = []
        self.floor_rect_world: pygame.Rect | None = None

        self.enemies: list = []
        self.enemy_bullets: list[EnemyBullet] = []
        self.pickups: list[Pickup] = []
        self._boss_reward_spawned = False

        self.state = self.STATE_IDLE
        self._cleared_event = False

        # graphics
        self._bg_cache: pygame.Surface | None = None
        self._bg_cache_key = None
        self._decor: list[tuple[pygame.Surface, pygame.Rect]] = []

        self._build_layout()

    def bg_color(self):
        defaults = {
            "start": (40, 40, 60),
            "boss": (80, 30, 30),
            "treasure": (60, 60, 30),
            "shop": (30, 60, 30),
            "secret": (60, 30, 60),
            "normal": getattr(settings, "BG_COLOR", (18, 18, 22)),
        }
        return defaults.get(self.room_type, defaults["normal"])

    # ---------------- FLOOR/WALL ----------------
    def _get_floor_rect_local(self) -> pygame.Rect:
        fr = getattr(settings, "ROOM_FLOOR_RECT_LOCAL", None)
        if isinstance(fr, (tuple, list)) and len(fr) == 4:
            return pygame.Rect(int(fr[0]), int(fr[1]), int(fr[2]), int(fr[3]))
        return DEFAULT_FLOOR_RECT_LOCAL.copy()

    def _build_walls_from_floor_rect(
        self,
        floor_rect_local: pygame.Rect,
        *,
        has_top: bool,
        has_bottom: bool,
        has_left: bool,
        has_right: bool,
    ):
        art = _room_art()
        ref = art.room_bg
        self.wall_rects = []
        self.floor_rect_world = None
        if ref is None:
            return

        b = self.bounds
        sx = b.w / ref.get_width()
        sy = b.h / ref.get_height()

        floor_world = pygame.Rect(
            b.left + int(floor_rect_local.x * sx),
            b.top + int(floor_rect_local.y * sy),
            int(floor_rect_local.w * sx),
            int(floor_rect_local.h * sy),
        )
        self.floor_rect_world = floor_world

        top = pygame.Rect(b.left, b.top, b.w, max(0, floor_world.top - b.top))
        bottom = pygame.Rect(b.left, floor_world.bottom, b.w, max(0, b.bottom - floor_world.bottom))
        left = pygame.Rect(b.left, floor_world.top, max(0, floor_world.left - b.left), floor_world.h)
        right = pygame.Rect(floor_world.right, floor_world.top, max(0, b.right - floor_world.right), floor_world.h)

        door_w = int(getattr(settings, "DOOR_SIZE", 140))
        cx, cy = b.centerx, b.centery

        def cut_horiz(wall: pygame.Rect) -> list[pygame.Rect]:
            hole = pygame.Rect(cx - door_w // 2, wall.top, door_w, wall.h)
            hole.clamp_ip(wall)
            parts = []
            if hole.left > wall.left:
                parts.append(pygame.Rect(wall.left, wall.top, hole.left - wall.left, wall.h))
            if hole.right < wall.right:
                parts.append(pygame.Rect(hole.right, wall.top, wall.right - hole.right, wall.h))
            return parts

        def cut_vert(wall: pygame.Rect) -> list[pygame.Rect]:
            hole = pygame.Rect(wall.left, cy - door_w // 2, wall.w, door_w)
            hole.clamp_ip(wall)
            parts = []
            if hole.top > wall.top:
                parts.append(pygame.Rect(wall.left, wall.top, wall.w, hole.top - wall.top))
            if hole.bottom < wall.bottom:
                parts.append(pygame.Rect(wall.left, hole.bottom, wall.w, wall.bottom - hole.bottom))
            return parts

        out: list[pygame.Rect] = []

        if top.h > 0:
            out += (cut_horiz(top) if has_top else [top])
        if bottom.h > 0:
            out += (cut_horiz(bottom) if has_bottom else [bottom])
        if left.w > 0:
            out += (cut_vert(left) if has_left else [left])
        if right.w > 0:
            out += (cut_vert(right) if has_right else [right])

        self.wall_rects = [r for r in out if r.w > 0 and r.h > 0]

    def rebuild_walls_for_neighbors(self, *, top: bool, bottom: bool, left: bool, right: bool):
        floor_rect_local = self._get_floor_rect_local()
        self._build_walls_from_floor_rect(
            floor_rect_local,
            has_top=bool(top),
            has_bottom=bool(bottom),
            has_left=bool(left),
            has_right=bool(right),
        )
        self._rebuild_solids()

    def _rebuild_solids(self):
        solids = [o.rect for o in self.objects if o.alive and o.is_solid()]
        solids.extend(self.wall_rects)
        self.solids = solids

    # ---------------- Layout helpers ----------------
    def _rotate90(self, mat: list[str]) -> list[str]:
        h = len(mat)
        w = len(mat[0])
        if w == h:
            return ["".join(mat[h - 1 - y][x] for y in range(h)) for x in range(h)]
        return ["".join(mat[h - 1 - y][x] for y in range(h)) for x in range(w)]

    def _mirror_h(self, mat: list[str]) -> list[str]:
        return [row[::-1] for row in mat]

    def _rng(self) -> random.Random:
        base = 0 if self.floor_seed is None else int(self.floor_seed)
        return random.Random((base * 1000003) ^ (self.cell * 1237) ^ 0x5A17)

    def _pick_layout(self, rng: random.Random) -> list[str]:
        if self.room_type == "start":
            return [".........." for _ in range(9)]

        if self.room_type == "boss":
            base = rng.choice(LAYOUTS_BOSS)
        elif self.room_type == "secret":
            base = rng.choice(LAYOUTS_SECRET)
        elif self.room_type == "shop":
            base = rng.choice(LAYOUTS_SHOP)
        elif self.room_type == "treasure":
            base = rng.choice(LAYOUTS_TREASURE)
        else:
            base = rng.choice(LAYOUTS_NORMAL)

        mat = base[:]
        rot = rng.randint(0, 3)
        for _ in range(rot):
            mat = self._rotate90(mat)
        if rng.random() < 0.5:
            mat = self._mirror_h(mat)
        return mat

    def _door_corridor_forbidden(self) -> list[pygame.Rect]:
        b = self.bounds
        size = int(getattr(settings, "DOOR_SIZE", 140))
        depth = max(int(getattr(settings, "DOOR_ZONE_DEPTH", 26)), 26) + 18
        cx = b.centerx
        cy = b.centery
        top = pygame.Rect(cx - size // 2, b.top, size, depth)
        bottom = pygame.Rect(cx - size // 2, b.bottom - depth, size, depth)
        left = pygame.Rect(b.left, cy - size // 2, depth, size)
        right = pygame.Rect(b.right - depth, cy - size // 2, depth, size)
        return [top, bottom, left, right]

    def _build_from_matrix(self, mat: list[str], rng: random.Random):
        self.objects.clear()

        h = len(mat)
        w = len(mat[0])

        inner = self.bounds.inflate(-120, -120)
        if inner.w < 200 or inner.h < 200:
            inner = self.bounds.inflate(-160, -160)

        cell_w = inner.w // w
        cell_h = inner.h // h
        cell = max(18, min(cell_w, cell_h))

        grid_w = w * cell
        grid_h = h * cell
        start_x = inner.centerx - grid_w // 2
        start_y = inner.centery - grid_h // 2

        forbidden = self._door_corridor_forbidden()
        placed_solids: list[pygame.Rect] = []

        def rect_for(ix: int, iy: int) -> pygame.Rect:
            pad = 3
            x = start_x + ix * cell + pad
            y = start_y + iy * cell + pad
            return pygame.Rect(x, y, cell - 2 * pad, cell - 2 * pad)

        for iy, row in enumerate(mat):
            for ix, ch in enumerate(row):
                if ch == ".":
                    continue
                r = rect_for(ix, iy)

                if any(r.colliderect(z) for z in forbidden):
                    continue
                if any(r.colliderect(p) for p in placed_solids):
                    continue

                if ch == "R":
                    self.objects.append(Rock(r))
                    placed_solids.append(r)
                elif ch == "C":
                    self.objects.append(Crate(r))
                    placed_solids.append(r)
                elif ch == "S":
                    self.objects.append(Spikes(r))

    def _spawn_enemies(self, rng: random.Random):
        self.enemies.clear()
        self.enemy_bullets.clear()
        self.pickups.clear()
        self._boss_reward_spawned = False

        if self.room_type == "start":
            return

        if self.room_type == "shop":
            cx, cy = self.bounds.center
            spread = 120
            spots = [(cx - spread, cy), (cx, cy), (cx + spread, cy)]
            for pos in spots:
                self.pickups.append(Pickup(pos, "random_loot"))
            return

        if self.room_type == "treasure":
            self.pickups.append(Pickup(self.bounds.center, "random_loot"))
            return

        if self.room_type == "boss":
            cx, cy = self.bounds.center
            self.enemies.append(BossPhase1(cx, cy))
            return

        def try_enemy():
            x = rng.randint(self.bounds.left + 160, self.bounds.right - 160)
            y = rng.randint(self.bounds.top + 160, self.bounds.bottom - 160)

            roll = rng.random()
            if roll < 0.45:
                e = EnemyChaser(x, y)
            elif roll < 0.70:
                e = EnemyShooter(x, y)
            elif roll < 0.82:
                e = EnemyTurret(x, y)
            elif roll < 0.92:
                e = EnemyDasher(x, y)
            elif roll < 0.98:
                e = EnemySummoner(x, y)
            else:
                e = EnemyTank(x, y)

            if any(e.rect.colliderect(s) for s in self.solids):
                return None
            return e

        count = 1 if self.room_type == "secret" else rng.randint(1, 3)
        if self.difficulty_scale >= 1.25:
            count += 1
        if self.difficulty_scale >= 1.75:
            count += 1

        for _ in range(count * 12):
            if len(self.enemies) >= count:
                break
            e = try_enemy()
            if e is not None:
                self.enemies.append(e)

    def _regen_decor(self, rng: random.Random):
        self._decor.clear()
        art = _room_art()
        if (not art.ok) or (not art.detail_sprites):
            return

        pad = TILE * 2
        area = self.bounds.inflate(-pad * 2, -pad * 2)
        if area.w <= 0 or area.h <= 0:
            return

        count = int(getattr(settings, "ROOM_DECOR_COUNT", rng.randint(6, 14)))
        for _ in range(count):
            spr = rng.choice(art.detail_sprites)
            sw, sh = spr.get_size()
            scale = min(TILE / max(1, sw), TILE / max(1, sh)) * rng.uniform(0.8, 1.2)
            dw = max(1, int(sw * scale))
            dh = max(1, int(sh * scale))
            img = pygame.transform.scale(spr, (dw, dh))

            x = rng.randint(area.left, max(area.left, area.right - dw))
            y = rng.randint(area.top, max(area.top, area.bottom - dh))
            self._decor.append((img, pygame.Rect(x, y, dw, dh)))

    def _build_layout(self):
        rng = self._rng()
        mat = self._pick_layout(rng)
        self._build_from_matrix(mat, rng)

        floor_rect_local = self._get_floor_rect_local()
        self._build_walls_from_floor_rect(
            floor_rect_local,
            has_top=False, has_bottom=False, has_left=False, has_right=False
        )
        self._rebuild_solids()

        self._spawn_enemies(rng)

        self._bg_cache = None
        self._bg_cache_key = None
        self._regen_decor(rng)

    # ---------------- State ----------------
    def consume_cleared_event(self) -> bool:
        if self._cleared_event:
            self._cleared_event = False
            return True
        return False

    def enter(self):
        self.enemy_bullets.clear()
        self._cleared_event = False

        if self.room_type in ("start", "shop", "treasure"):
            self.state = self.STATE_CLEARED
            return

        has_alive = any(getattr(e, "alive", True) for e in self.enemies)
        self.state = self.STATE_COMBAT if has_alive else self.STATE_CLEARED

    def is_cleared(self) -> bool:
        return self.state == self.STATE_CLEARED

    def maybe_spawn_boss_reward(self):
        if self.room_type != "boss":
            return
        if self._boss_reward_spawned:
            return
        if not self.is_cleared():
            return
        self._boss_reward_spawned = True
        self.pickups.append(Pickup(self.bounds.center, "token_upgrade"))

    def update(self, dt: float, player_rect: pygame.Rect):
        for o in self.objects:
            o.update(dt)

        self.objects = [o for o in self.objects if o.alive or isinstance(o, Spikes)]
        self._rebuild_solids()

        for e in self.enemies:
            e.update(dt, player_rect, self.solids, self.bounds, enemies=self.enemies)
        self.enemies = [e for e in self.enemies if getattr(e, "alive", True)]

        for e in self.enemies:
            if hasattr(e, "pop_shots"):
                bullets = e.pop_shots(player_rect, self.solids)
                if bullets:
                    self.enemy_bullets.extend(bullets)
                continue
            if hasattr(e, "pop_shot"):
                b = e.pop_shot(player_rect, self.solids)
                if b is not None:
                    self.enemy_bullets.append(b)

        for e in list(self.enemies):
            if hasattr(e, "pop_spawns"):
                spawned = e.pop_spawns()
                if spawned:
                    self.enemies.extend(spawned)

        for b in self.enemy_bullets:
            b.update(dt, self.solids, self.bounds)
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]

        if self.state == self.STATE_COMBAT:
            if not any(getattr(e, "alive", True) for e in self.enemies):
                self.state = self.STATE_CLEARED
                self._cleared_event = True

        self.maybe_spawn_boss_reward()

    # ---------------- Graphics ----------------
    def _build_bg_cache(self) -> pygame.Surface:
        """
        Фон комнаты = стены + пол.
        Требование: room_walls.png и room_floor.png одинакового размера.
        """
        key = (self.bounds.size, self.room_type)
        if self._bg_cache is not None and self._bg_cache_key == key:
            return self._bg_cache

        surf = pygame.Surface(self.bounds.size, pygame.SRCALPHA)
        art = _room_art()

        if (not art.ok) or (art.room_walls is None and art.room_floor is None):
            surf.fill(self.bg_color())
            self._bg_cache = surf
            self._bg_cache_key = key
            return self._bg_cache

        if art.room_walls is not None:
            walls_scaled = pygame.transform.scale(art.room_walls, self.bounds.size)
            surf.blit(walls_scaled, (0, 0))
        else:
            surf.fill(self.bg_color())

        if art.room_floor is not None:
            floor_scaled = pygame.transform.scale(art.room_floor, self.bounds.size)
            surf.blit(floor_scaled, (0, 0))

        self._bg_cache = surf
        self._bg_cache_key = key
        return self._bg_cache

    def draw_doors(
        self,
        screen: pygame.Surface,
        *,
        top: bool,
        bottom: bool,
        left: bool,
        right: bool,
        opened: bool
    ):
        art = _room_art()
        if (not art.ok) or (art.door_closed is None):
            return

        base = art.door_open if (opened and art.door_open is not None) else art.door_closed

        b = self.bounds
        size = int(getattr(settings, "DOOR_SIZE", 140))
        depth = int(getattr(settings, "DOOR_ZONE_DEPTH", 26))
        cx = b.centerx
        cy = b.centery

        r_top = pygame.Rect(cx - size // 2, b.top, size, depth)
        r_bottom = pygame.Rect(cx - size // 2, b.bottom - depth, size, depth)
        r_left = pygame.Rect(b.left, cy - size // 2, depth, size)
        r_right = pygame.Rect(b.right - depth, cy - size // 2, depth, size)

        def draw_variant(img: pygame.Surface, rect: pygame.Rect, kind: str):
            if kind == "top":
                spr = img
            elif kind == "bottom":
                spr = pygame.transform.flip(img, False, True)
            elif kind == "left":
                spr = pygame.transform.rotate(img, 90)
            else:
                spr = pygame.transform.rotate(img, -90)

            spr = pygame.transform.scale(spr, (rect.w, rect.h))
            screen.blit(spr, rect.topleft)

        if top:
            draw_variant(base, r_top, "top")
        if bottom:
            draw_variant(base, r_bottom, "bottom")
        if left:
            draw_variant(base, r_left, "left")
        if right:
            draw_variant(base, r_right, "right")

    def draw(self, screen: pygame.Surface):
        bg = self._build_bg_cache()
        screen.blit(bg, self.bounds.topleft)

        for img, r in self._decor:
            screen.blit(img, r.topleft)

        art = _room_art()

        for o in self.objects:
            if not getattr(o, "alive", True):
                continue

            if isinstance(o, Rock) and (art.ok and art.rock_gray is not None):
                img = pygame.transform.scale(art.rock_gray, (o.rect.w, o.rect.h))
                screen.blit(img, o.rect.topleft)
                continue

            if isinstance(o, Crate) and (art.ok and art.rock_brown is not None):
                img = pygame.transform.scale(art.rock_brown, (o.rect.w, o.rect.h))
                screen.blit(img, o.rect.topleft)
                continue

            o.draw(screen)

        for p in self.pickups:
            if hasattr(p, "draw"):
                p.draw(screen)

        for b in self.enemy_bullets:
            b.draw(screen)

        for e in self.enemies:
            e.draw(screen)

        if bool(getattr(settings, "DEBUG_WALLS", False)):
            if self.floor_rect_world:
                pygame.draw.rect(screen, (0, 255, 0), self.floor_rect_world, 2)
            for r in self.wall_rects:
                pygame.draw.rect(screen, (255, 0, 0), r, 2)