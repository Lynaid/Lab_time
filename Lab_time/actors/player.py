# actors/player.py
from __future__ import annotations

import os
import re
import pygame
import settings

from combat.melee import MeleeWeapon
from combat.abilities import FastShot, BulletCycle, AtomicBlast, ArtilleryRain
from combat.upgrades import UpgradeManager


def _project_root() -> str:
    # actors/ -> project root (where assets/ lives)
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, ".."))


def _player_anim_root() -> str:
    # assets/sprites/GEKKORAR-STUFF/...
    return os.path.join(_project_root(), "assets", "sprites", "GEKKORAR-STUFF")


def _natural_sort_key(name: str):
    # walk_side1.png, walk_side10.png ... => correct numeric order
    parts = re.split(r"(\d+)", name.lower())
    out = []
    for p in parts:
        out.append(int(p) if p.isdigit() else p)
    return out


def _load_anim_frames(folder: str, scale: float) -> list[pygame.Surface]:
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Animation folder not found: {folder}")

    files = [
        f for f in os.listdir(folder)
        if f.lower().endswith(".png") and os.path.isfile(os.path.join(folder, f))
    ]
    files.sort(key=_natural_sort_key)

    frames: list[pygame.Surface] = []
    for fname in files:
        img = pygame.image.load(os.path.join(folder, fname)).convert_alpha()

        # scale (nearest => no blur)
        if scale != 1.0:
            w = max(1, int(round(img.get_width() * scale)))
            h = max(1, int(round(img.get_height() * scale)))
            img = pygame.transform.scale(img, (w, h))

        frames.append(img)

    if not frames:
        raise RuntimeError(f"No PNG frames in folder: {folder}")

    return frames


class SimpleAnim:
    def __init__(self, frames: list[pygame.Surface], fps: float, loop: bool = True):
        self.frames = frames
        self.fps = float(fps)
        self.loop = bool(loop)
        self.time = 0.0
        self.index = 0
        self.done = False

    def reset(self):
        self.time = 0.0
        self.index = 0
        self.done = False

    def update(self, dt: float):
        if self.done or len(self.frames) <= 1:
            return

        step = 1.0 / max(1e-6, self.fps)
        self.time += float(dt)

        while self.time >= step and not self.done:
            self.time -= step
            self.index += 1
            if self.index >= len(self.frames):
                if self.loop:
                    self.index = 0
                else:
                    self.index = len(self.frames) - 1
                    self.done = True

    def get_frame(self) -> pygame.Surface:
        return self.frames[self.index]


class Player:
    """
    ВАЖНО:
      - self.rect = hitbox (placeholder) и используется для коллизий/урона как раньше.
      - визуал (спрайт) рисуется отдельно и НЕ влияет на физику.
    """

    def __init__(self, x: float, y: float, run_seed: int = 1):
        self.run_seed = int(run_seed)

        s = int(getattr(settings, "PLAYER_SIZE", 40))
        self.rect = pygame.Rect(int(x - s / 2), int(y - s / 2), s, s)

        self.pos = pygame.Vector2(self.rect.centerx, self.rect.centery)
        self.vel = pygame.Vector2(0, 0)

        self.max_hp = int(getattr(settings, "PLAYER_MAX_HP", 100))
        self.hp = int(getattr(settings, "PLAYER_MAX_HP", 100))
        self.iframes = 0.0

        self.attack_dir = pygame.Vector2(0, 1)
        self.move_speed_bonus = 0.0

        # melee
        self.weapon = MeleeWeapon("club")

        # abilities
        self.ability_q = FastShot()
        self.ability_r = BulletCycle()
        self.ability_e = AtomicBlast()
        self.ability_f = ArtilleryRain()

        # unlock flags (main project behavior: Q available, others can be unlocked)
        self.unlocked = {"Q": True, "R": False, "E": False, "F": False}

        # upgrades
        self.upgrades = UpgradeManager()

        # sprite / animation state
        self._facing = "down"  # "down"|"up"|"side"
        self._flip_x = False
        self._visual_attack_lock = 0.0
        self._anim_state = "idle_down"

        # scaling/offset
        self._anim_scale = float(getattr(settings, "PLAYER_SPRITE_SCALE", 0.35))
        self._anim_offset_y = int(getattr(settings, "PLAYER_SPRITE_OFFSET_Y", 6))

        # side flip: if SIDE frames are facing LEFT by default, then right requires flip
        self._side_flip_inverted = bool(getattr(settings, "PLAYER_SIDE_FLIP_INVERTED", True))

        # anims
        self._anims: dict[str, SimpleAnim] = {}
        self._load_player_anims()

    def _load_player_anims(self):
        root = _player_anim_root()

        idle_fps = float(getattr(settings, "PLAYER_IDLE_FPS", 14))
        walk_fps = float(getattr(settings, "PLAYER_WALK_FPS", 14))
        hit_fps = float(getattr(settings, "PLAYER_HIT_FPS", 24))  # 12 frames per 1 second target

        try:
            self._anims = {
                "idle_down": SimpleAnim(_load_anim_frames(os.path.join(root, "IDLE", "FRONT"), self._anim_scale), fps=idle_fps, loop=True),
                "idle_up":   SimpleAnim(_load_anim_frames(os.path.join(root, "IDLE", "BACK"),  self._anim_scale), fps=idle_fps, loop=True),
                "idle_side": SimpleAnim(_load_anim_frames(os.path.join(root, "IDLE", "SIDE"),  self._anim_scale), fps=idle_fps, loop=True),

                "run_down":  SimpleAnim(_load_anim_frames(os.path.join(root, "WALK", "FRONT"), self._anim_scale), fps=walk_fps, loop=True),
                "run_up":    SimpleAnim(_load_anim_frames(os.path.join(root, "WALK", "BACK"),  self._anim_scale), fps=walk_fps, loop=True),
                "run_side":  SimpleAnim(_load_anim_frames(os.path.join(root, "WALK", "SIDE"),  self._anim_scale), fps=walk_fps, loop=True),

                # эти кадры — анимация персонажа удара (не white-stuff)
                "melee_down": SimpleAnim(_load_anim_frames(os.path.join(root, "HIT", "FRONT"), self._anim_scale), fps=hit_fps, loop=True),
                "melee_up":   SimpleAnim(_load_anim_frames(os.path.join(root, "HIT", "BACK"),  self._anim_scale), fps=hit_fps, loop=True),
                "melee_side": SimpleAnim(_load_anim_frames(os.path.join(root, "HIT", "SIDE"),  self._anim_scale), fps=hit_fps, loop=True),
            }
        except Exception as e:
            print("[PLAYER SPRITE LOAD FAIL]", e)
            self._anims = {}

    # -------------------------
    # compatibility helpers (main.py expects these)
    # -------------------------
    def set_center(self, cx: float, cy: float):
        self.rect.center = (int(cx), int(cy))
        self.pos.update(self.rect.centerx, self.rect.centery)

    def set_pos(self, x: float, y: float):
        self.rect.topleft = (int(x), int(y))
        self.pos.update(self.rect.centerx, self.rect.centery)

    def has_ability(self, key: str) -> bool:
        return bool(self.unlocked.get(str(key).upper(), False))

    def unlock_ability(self, key: str):
        self.unlocked[str(key).upper()] = True

    def heal(self, amount: int):
        a = int(amount)
        if a <= 0:
            return
        self.hp = min(self.max_hp, self.hp + a)

    def take_damage(self, dmg: int):
        if self.iframes > 0.0:
            return
        self.hp -= int(dmg)
        self.iframes = float(getattr(settings, "PLAYER_IFRAMES", 0.45))

    def get_melee_hitboxes(self) -> list[pygame.Rect]:
        if not hasattr(self, "weapon") or self.weapon is None:
            return []
        if not self.weapon.is_active():
            return []
        return self.weapon.build_hitboxes(self.rect)

    def is_melee_active(self) -> bool:
        if not hasattr(self, "weapon") or self.weapon is None:
            return False
        return bool(self.weapon.is_active())

    # -------------------------
    # INPUT (main.py calls: handle_input(projectiles, artillery_shells, bounds, effects))
    # -------------------------
    def handle_input(self, projectiles, artillery_shells, bounds: pygame.Rect, effects):
        keys = pygame.key.get_pressed()

        # movement (WASD)
        vx = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
        vy = (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)
        v = pygame.Vector2(vx, vy)
        if v.length_squared() > 0:
            v = v.normalize()
        self.vel = v

        # aim (ARROWS)
        ax = (1 if keys[pygame.K_RIGHT] else 0) - (1 if keys[pygame.K_LEFT] else 0)
        ay = (1 if keys[pygame.K_DOWN] else 0) - (1 if keys[pygame.K_UP] else 0)
        a = pygame.Vector2(ax, ay)
        if a.length_squared() > 0:
            self.attack_dir = a.normalize()

        # melee
        if keys[pygame.K_SPACE]:
            self.weapon.try_attack(self.attack_dir)
            self._visual_attack_lock = max(self._visual_attack_lock, 0.12)

        # abilities
        if keys[pygame.K_q] and self.has_ability("Q"):
            self.ability_q.cast(self, projectiles)

        if keys[pygame.K_r] and self.has_ability("R"):
            self.ability_r.cast(self)

        if keys[pygame.K_e] and self.has_ability("E"):
            self.ability_e.cast(self, effects)

        if keys[pygame.K_f] and self.has_ability("F"):
            self.ability_f.cast(self, artillery_shells, bounds)

    # -------------------------
    # UPDATE (main.py calls: update(dt, solids, bounds, projectiles))
    # -------------------------
    def update(self, dt: float, solids, bounds: pygame.Rect, projectiles):
        # i-frames
        if self.iframes > 0.0:
            self.iframes = max(0.0, self.iframes - float(dt))

        # cooldowns / queues
        self.ability_q.update_cd(dt)
        self.ability_r.update(dt, self, projectiles)
        self.ability_e.update(dt)

        # movement
        base_speed = float(getattr(settings, "PLAYER_SPEED", 260))
        speed = base_speed + float(self.move_speed_bonus)
        move = self.vel * speed * float(dt)

        # axis-separated collision
        if move.x != 0:
            self.rect.x += int(round(move.x))
            for r in solids:
                if self.rect.colliderect(r):
                    if move.x > 0:
                        self.rect.right = r.left
                    else:
                        self.rect.left = r.right

        if move.y != 0:
            self.rect.y += int(round(move.y))
            for r in solids:
                if self.rect.colliderect(r):
                    if move.y > 0:
                        self.rect.bottom = r.top
                    else:
                        self.rect.top = r.bottom

        # clamp to bounds
        if bounds:
            self.rect.left = max(bounds.left, self.rect.left)
            self.rect.right = min(bounds.right, self.rect.right)
            self.rect.top = max(bounds.top, self.rect.top)
            self.rect.bottom = min(bounds.bottom, self.rect.bottom)

        self.pos.update(self.rect.centerx, self.rect.centery)

        # melee
        self.weapon.update(float(dt))

        # sprite
        self._update_sprite(float(dt))

    # -------------------------
    # SPRITE STATE
    # -------------------------
    def _set_anim_state(self, new_state: str):
        if new_state == self._anim_state:
            return
        self._anim_state = new_state
        anim = self._anims.get(self._anim_state)
        if anim is not None:
            anim.reset()

    def _update_sprite(self, dt: float):
        if not self._anims:
            return

        # facing from attack_dir
        d = pygame.Vector2(self.attack_dir)
        if d.length_squared() > 0:
            if abs(d.x) > abs(d.y):
                self._facing = "side"
                # left/right fix for SIDE frames
                # inverted=True means: frames face LEFT by default, so RIGHT needs flip
                self._flip_x = (d.x > 0) if self._side_flip_inverted else (d.x < 0)
            else:
                self._facing = "up" if d.y < 0 else "down"
                self._flip_x = False

        moving = self.vel.length_squared() > 1e-6
        attacking = (self._visual_attack_lock > 0.0) or getattr(self.weapon, "_state", "ready") in ("windup", "active")

        if attacking:
            self._visual_attack_lock = max(0.0, self._visual_attack_lock - dt)
            if self._facing == "side":
                self._set_anim_state("melee_side")
            elif self._facing == "up":
                self._set_anim_state("melee_up")
            else:
                self._set_anim_state("melee_down")
        else:
            if moving:
                self._set_anim_state(f"run_{self._facing}")
            else:
                self._set_anim_state(f"idle_{self._facing}")

        anim = self._anims.get(self._anim_state)
        if anim is not None:
            anim.update(dt)

    # -------------------------
    # DRAW
    # -------------------------
    def draw(self, screen: pygame.Surface, *, debug_hitbox: bool = False):
        if not self._anims:
            pygame.draw.rect(screen, (230, 230, 240), self.rect)
            pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
            return

        anim = self._anims.get(self._anim_state)
        if anim is None or not anim.frames:
            pygame.draw.rect(screen, (230, 230, 240), self.rect)
            pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
            return

        img = anim.get_frame()
        if self._flip_x:
            img = pygame.transform.flip(img, True, False)

        draw_rect = img.get_rect(midbottom=self.rect.midbottom)
        draw_rect.y += self._anim_offset_y
        screen.blit(img, draw_rect.topleft)

        # FX hitbox visual is drawn by MeleeWeapon (white-stuff) when active
        # (requires updated melee.py with draw_attack_fx)
        screen.blit(img, draw_rect.topleft)

        self.weapon.draw_hitboxes_debug(screen, self.rect)

        if debug_hitbox:
            pygame.draw.rect(screen, (255, 255, 0), self.rect, 1)