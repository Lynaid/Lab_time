# main.py
import pygame
import settings

from core.scene import SceneManager, Scene
from actors.player import Player
from ui.hud import HUD
from ui.minimap import MiniMap
from world.map_gen import generate_rooms
from world.room import Room
from world.objects import Crate, Spikes, Rock
from ui.upgrade_menu import UpgradeSelectScene

from audio.audio_manager import AUDIO, AudioManager, apply_audio_from_app
from config.app_config import APP
from ui.menus import MainMenuScene, PauseScene, GameOverScene


def cell_to_xy(cell: int):
    return cell % settings.MAP_W, cell // settings.MAP_W


def xy_to_cell(x: int, y: int):
    return y * settings.MAP_W + x


class GameScene(Scene):
    def __init__(self):
        self.player = Player(settings.SCREEN_W / 2, settings.SCREEN_H / 2)

        m = settings.ROOM_MARGIN
        self.bounds = pygame.Rect(m, m, settings.SCREEN_W - 2 * m, settings.SCREEN_H - 2 * m)

        self.hud = HUD()
        self.minimap = MiniMap()

        self.projectiles = []
        self.artillery_shells = []
        self.effects = []

        self.floor = 1

        self._enemy_hp_prev: dict[int, int] = {}
        self._enemy_alive_prev: dict[int, bool] = {}
        self._crate_alive_prev: dict[int, bool] = {}
        self._rock_alive_prev: dict[int, bool] = {}

        # portal state
        self.portal_active = False
        self.portal_rect: pygame.Rect | None = None
        self.portal_cell: int | None = None  # bind portal to boss cell
        self._portal_spawned_for_floor = 0
        self._portal_key_pressed = False

        pygame.font.init()
        self._hint_font = pygame.font.SysFont("consolas", 18)

        self._prev_hp = int(getattr(self.player, "hp", 0))

        seed = settings.FORCE_SEED
        self._build_floor(seed=seed)

    def _build_floor(self, seed: int | None):
        self.room_cells, self.room_types, self.seed = generate_rooms(seed=seed)

        diff = {"scale": float(APP.difficulty_scale)}
        self.rooms: dict[int, Room] = {
            cell: Room(cell, self.bounds, self.room_types.get(cell, "normal"), difficulty=diff)
            for cell in self.room_cells
        }

        self.current_cell = int(getattr(settings, "START_CELL", 0))
        if self.current_cell not in self.rooms:
            starts = [c for c, t in self.room_types.items() if t == "start" and c in self.rooms]
            self.current_cell = starts[0] if starts else next(iter(self.rooms.keys()))

        self.current_room = self.rooms[self.current_cell]
        self.current_room.enter()
        self.visited_cells: set[int] = {self.current_cell}

        if not hasattr(self.current_room, "pickups"):
            self.current_room.pickups = []

        # reset portal ONLY when building a new floor
        self.portal_active = False
        self.portal_rect = None
        self.portal_cell = None
        self._portal_spawned_for_floor = 0
        self._portal_key_pressed = False

        self.player.set_center(self.bounds.centerx, self.bounds.centery)

        self.projectiles.clear()
        self.artillery_shells.clear()
        self.effects.clear()

        self._prev_hp = int(getattr(self.player, "hp", 0))

        self._enemy_hp_prev.clear()
        self._enemy_alive_prev.clear()
        self._crate_alive_prev.clear()
        self._rock_alive_prev.clear()

    def _next_floor(self):
        self.floor += 1
        new_seed = (int(self.seed) * 1103515245 + 12345 + self.floor * 99991) & 0x7FFFFFFF
        self._build_floor(seed=new_seed)

    def _door_rects(self):
        b = self.bounds
        depth = settings.DOOR_ZONE_DEPTH
        size = settings.DOOR_SIZE
        cx = b.centerx
        cy = b.centery
        top = pygame.Rect(cx - size // 2, b.top, size, depth)
        bottom = pygame.Rect(cx - size // 2, b.bottom - depth, size, depth)
        left = pygame.Rect(b.left, cy - size // 2, depth, size)
        right = pygame.Rect(b.right - depth, cy - size // 2, depth, size)
        return top, bottom, left, right

    def _has_neighbor(self, dx: int, dy: int) -> bool:
        cx, cy = cell_to_xy(self.current_cell)
        nx, ny = cx + dx, cy + dy
        if not (0 <= nx < settings.MAP_W and 0 <= ny < settings.MAP_H):
            return False
        return xy_to_cell(nx, ny) in self.rooms

    def _try_change_room(self, dx: int, dy: int):
        cx, cy = cell_to_xy(self.current_cell)
        nx, ny = cx + dx, cy + dy
        if not (0 <= nx < settings.MAP_W and 0 <= ny < settings.MAP_H):
            return False
        new_cell = xy_to_cell(nx, ny)
        if new_cell not in self.rooms:
            return False

        self.current_cell = new_cell
        self.current_room = self.rooms[new_cell]
        self.current_room.enter()
        self.visited_cells.add(self.current_cell)

        if not hasattr(self.current_room, "pickups"):
            self.current_room.pickups = []

        self.projectiles.clear()
        self.artillery_shells.clear()
        self.effects.clear()

        pad = settings.DOOR_SPAWN_OFFSET
        if dx == 1:
            self.player.set_center(self.bounds.left + pad, self.player.rect.centery)
        elif dx == -1:
            self.player.set_center(self.bounds.right - pad, self.player.rect.centery)
        elif dy == 1:
            self.player.set_center(self.player.rect.centerx, self.bounds.top + pad)
        elif dy == -1:
            self.player.set_center(self.player.rect.centerx, self.bounds.bottom - pad)

        self._enemy_hp_prev.clear()
        self._enemy_alive_prev.clear()
        self._crate_alive_prev.clear()
        self._rock_alive_prev.clear()

        # IMPORTANT: do NOT disable portal here.
        # Portal visibility/interaction is strictly gated in _draw_portal/_portal_interaction.

        AUDIO.play_sfx("door_travel", channel=AudioManager.CH_WORLD)
        return True

    def _clamp_inside_bounds(self):
        b = self.bounds
        if self.player.rect.left < b.left:
            self.player.rect.left = b.left
        if self.player.rect.right > b.right:
            self.player.rect.right = b.right
        if self.player.rect.top < b.top:
            self.player.rect.top = b.top
        if self.player.rect.bottom > b.bottom:
            self.player.rect.bottom = b.bottom
        self.player.set_center(self.player.rect.centerx, self.player.rect.centery)

    def _door_transitions(self):
        if not self.current_room.is_cleared():
            self._clamp_inside_bounds()
            return

        top, bottom, left, right = self._door_rects()

        if self._has_neighbor(1, 0) and self.player.rect.colliderect(right):
            if self._try_change_room(1, 0):
                return
        if self._has_neighbor(-1, 0) and self.player.rect.colliderect(left):
            if self._try_change_room(-1, 0):
                return
        if self._has_neighbor(0, 1) and self.player.rect.colliderect(bottom):
            if self._try_change_room(0, 1):
                return
        if self._has_neighbor(0, -1) and self.player.rect.colliderect(top):
            if self._try_change_room(0, -1):
                return

        self._clamp_inside_bounds()

    def _draw_walls_and_doors(self, screen):
        pygame.draw.rect(screen, settings.WALL_COLOR, self.bounds, width=settings.WALL_THICKNESS)
        opened = self.current_room.is_cleared()
        top, bottom, left, right = self._door_rects()

        floor_color = self.current_room.bg_color() if hasattr(self.current_room, "bg_color") else settings.BG_COLOR
        door_fill = settings.WALL_COLOR
        door_locked_outline = (90, 90, 105)
        door_outline = (0, 0, 0)

        def draw_open(r: pygame.Rect):
            pygame.draw.rect(screen, floor_color, r)
            pygame.draw.rect(screen, door_outline, r, 1)

        def draw_closed(r: pygame.Rect):
            pygame.draw.rect(screen, door_fill, r)
            pygame.draw.rect(screen, door_locked_outline, r, 2)

        if self._has_neighbor(0, -1):
            draw_open(top) if opened else draw_closed(top)
        if self._has_neighbor(0, 1):
            draw_open(bottom) if opened else draw_closed(bottom)
        if self._has_neighbor(-1, 0):
            draw_open(left) if opened else draw_closed(left)
        if self._has_neighbor(1, 0):
            draw_open(right) if opened else draw_closed(right)

    def _ensure_portal_after_boss(self):
        # portal is bound to the boss room cell
        if self.current_room.room_type != "boss":
            return
        if not self.current_room.is_cleared():
            return
        if self._portal_spawned_for_floor == self.floor:
            return

        size = int(settings.NEXT_FLOOR_PORTAL_SIZE)
        self.portal_rect = pygame.Rect(0, 0, size, size)
        self.portal_rect.center = self.bounds.center

        self.portal_active = True
        self.portal_cell = self.current_cell
        self._portal_spawned_for_floor = self.floor

        AUDIO.play_sfx("portal", channel=AudioManager.CH_WORLD)

    def _portal_interaction(self):
        if not self.portal_active or self.portal_rect is None:
            return
        # STRICT: portal works only in its boss cell
        if self.portal_cell is None or self.current_cell != self.portal_cell:
            return

        if not self.player.rect.colliderect(self.portal_rect):
            self._portal_key_pressed = False
            return

        if not settings.NEXT_FLOOR_REQUIRES_KEY:
            self._next_floor()
            return

        key = settings.NEXT_FLOOR_KEY or pygame.K_RETURN

        keys = pygame.key.get_pressed()
        if keys[key]:
            if not self._portal_key_pressed:
                self._portal_key_pressed = True
                self._next_floor()
        else:
            self._portal_key_pressed = False

    def _draw_portal(self, screen):
        if not self.portal_active or self.portal_rect is None:
            return
        # STRICT: portal is drawn only in its boss cell
        if self.portal_cell is None or self.current_cell != self.portal_cell:
            return

        pygame.draw.rect(screen, settings.NEXT_FLOOR_PORTAL_COLOR, self.portal_rect)
        pygame.draw.rect(screen, settings.NEXT_FLOOR_PORTAL_OUTLINE, self.portal_rect, 2)

        if settings.NEXT_FLOOR_REQUIRES_KEY and self.player.rect.colliderect(self.portal_rect):
            txt = self._hint_font.render("ENTER -> NEXT FLOOR", True, settings.NEXT_FLOOR_HINT_COLOR)
            screen.blit(txt, (self.portal_rect.centerx - txt.get_width() // 2, self.portal_rect.top - 26))

    def _apply_enemy_contact_damage(self):
        for e in self.current_room.enemies:
            if not getattr(e, "alive", True):
                continue
            if getattr(e, "contact_damage", 0) <= 0:
                continue
            if not hasattr(e, "can_deal_contact_now") or not hasattr(e, "mark_contact_dealt"):
                continue
            if e.rect.colliderect(self.player.rect) and e.can_deal_contact_now():
                self.player.take_damage(int(e.contact_damage))
                e.mark_contact_dealt()

    def _update_ambience(self):
        rt = getattr(self.current_room, "room_type", "normal")
        if rt not in ("normal", "boss", "secret", "shop", "treasure", "start"):
            rt = "normal"
        if rt == "start":
            rt = "normal"
        AUDIO.set_ambience(rt)

    def _pickup_interactions(self):
        if not hasattr(self.current_room, "pickups"):
            return

        for p in list(self.current_room.pickups):
            if not getattr(p, "alive", True):
                continue
            if not hasattr(p, "rect"):
                continue

            if self.player.rect.colliderect(p.rect):
                result = p.apply(self.player)
                p.alive = False
                AUDIO.play_ui("select")

                # result can be dict (open menu), Pickup (drop), None
                if isinstance(result, dict):
                    action = result.get("action")
                    if action == "upgrade_menu":
                        seed = int(result.get("seed", 1))
                        allow_skip = bool(result.get("allow_skip", False))
                        title = str(result.get("title", "CHOOSE UPGRADE"))

                        from ui.upgrade_menu import UpgradeSelectScene
                        scene = UpgradeSelectScene(self, rng_seed=seed, allow_skip=allow_skip, title=title)
                        scene.manager = self.manager
                        self.manager.switch(scene)
                        return

# IMPORTANT: DO NOT add dict to room.pickups

                elif result is not None:
                    if hasattr(result, "rect") and hasattr(result, "draw"):
                        self.current_room.pickups.append(result)

        # ckear
        self.current_room.pickups = [x for x in self.current_room.pickups if getattr(x, "alive", True)]

    def _update_feedback_sfx(self):
        alive_now = {}
        hp_now = {}
        for e in self.current_room.enemies:
            eid = id(e)
            alive = bool(getattr(e, "alive", True))
            alive_now[eid] = alive

            hp = getattr(e, "hp", None)
            if hp is None:
                hp = getattr(e, "health", 0)
            hp = int(hp)
            hp_now[eid] = hp

            prev_alive = self._enemy_alive_prev.get(eid, alive)
            prev_hp = self._enemy_hp_prev.get(eid, hp)

            if alive and hp < prev_hp:
                AUDIO.play_sfx("enemy_hit", channel=AudioManager.CH_WORLD)
            if prev_alive and (not alive):
                AUDIO.play_sfx("enemy_die", channel=AudioManager.CH_WORLD)

        self._enemy_alive_prev = alive_now
        self._enemy_hp_prev = hp_now

        crates_now = {}
        rocks_now = {}
        for o in self.current_room.objects:
            oid = id(o)
            alive = bool(getattr(o, "alive", True))
            if isinstance(o, Crate):
                prev = self._crate_alive_prev.get(oid, alive)
                if prev and (not alive):
                    AUDIO.play_sfx("crate_break", channel=AudioManager.CH_WORLD)
                crates_now[oid] = alive
            elif isinstance(o, Rock):
                prev = self._rock_alive_prev.get(oid, alive)
                if prev and (not alive):
                    AUDIO.play_sfx("rock_break", channel=AudioManager.CH_WORLD)
                rocks_now[oid] = alive

        self._crate_alive_prev = crates_now
        self._rock_alive_prev = rocks_now

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pause = PauseScene(self, make_game_scene=make_game_scene, make_main_menu=make_main_menu)
                pause.manager = self.manager
                self.manager.switch(pause)
                return

    def update(self, dt: float):
        rt = getattr(self.current_room, "room_type", "normal")
        boss_track_exists = bool(AUDIO.music_tracks.get("boss"))
        if rt == "boss" and (not self.current_room.is_cleared()) and boss_track_exists:
            AUDIO.play_music("boss", loop=True, fade_ms=350)
        else:
            AUDIO.play_music("game", loop=True, fade_ms=250)
        self._update_ambience()

        if int(getattr(self.player, "hp", 1)) <= 0:
            over = GameOverScene(self.floor, int(self.seed), make_game_scene=make_game_scene, make_main_menu=make_main_menu)
            over.manager = self.manager
            self.manager.switch(over)
            return

        before_proj = len(self.projectiles)
        before_shells = len(self.artillery_shells)
        before_fx = len(self.effects)
        before_swing = int(getattr(self.player.weapon, "swing_id", 0))
        r_prev_queue = int(getattr(self.player.ability_r, "queue_left", 0))

        # INPUT (must run every frame)
        self.player.handle_input(self.projectiles, self.artillery_shells, self.bounds, self.effects)

        after_proj = len(self.projectiles)
        after_shells = len(self.artillery_shells)
        after_fx = len(self.effects)
        after_swing = int(getattr(self.player.weapon, "swing_id", 0))
        r_now_queue = int(getattr(self.player.ability_r, "queue_left", 0))

        r_started = (r_prev_queue <= 0 and r_now_queue > 0)
        if r_started:
            AUDIO.play_sfx("r", channel=AudioManager.CH_PLAYER)
        if after_proj > before_proj and not r_started:
            AUDIO.play_sfx("q", channel=AudioManager.CH_PLAYER)
        if after_shells > before_shells:
            AUDIO.play_sfx("f", channel=AudioManager.CH_WORLD)
        if after_fx > before_fx:
            AUDIO.play_sfx("e", channel=AudioManager.CH_WORLD)
        if after_swing != before_swing:
            AUDIO.play_sfx("melee", channel=AudioManager.CH_PLAYER)

        self.player.update(dt, self.current_room.solids, self.bounds, self.projectiles)

        for o in self.current_room.objects:
            if isinstance(o, Spikes) and getattr(o, "alive", True):
                if self.player.rect.colliderect(o.rect):
                    self.player.take_damage(o.damage)

        self._door_transitions()

        for p in self.projectiles:
            p.update(dt, self.current_room.solids, self.bounds)

            if not p.alive:
                continue

            for o in self.current_room.objects:
                if isinstance(o, Crate) and o.alive and p.rect.colliderect(o.rect):
                    o.take_damage(p.damage)
                    if not p.piercing:
                        p.alive = False
                    break

        for p in self.projectiles:
            if not p.alive:
                continue
            for e in self.current_room.enemies:
                if getattr(e, "alive", True) and p.rect.colliderect(e.rect):
                    e.take_projectile_hit(p.damage)
                    if not p.piercing:
                        p.alive = False
                        break

        self.projectiles = [p for p in self.projectiles if p.alive]

        for s in self.artillery_shells:
            s.update(dt)
            s.try_apply(self.current_room.enemies)
        self.artillery_shells = [s for s in self.artillery_shells if s.alive]

        for fx in self.effects:
            fx.update(dt, self.current_room.enemies)
        self.effects = [fx for fx in self.effects if getattr(fx, "alive", True)]

        self.current_room.update(dt, self.player.rect)

        if hasattr(self.current_room, "consume_cleared_event") and self.current_room.consume_cleared_event():
            AUDIO.play_sfx("room_clear", channel=AudioManager.CH_WORLD)
            AUDIO.play_sfx("door_open", channel=AudioManager.CH_WORLD)

            # counter of cleaned rooms (except start/shop/treasure)
            if not hasattr(self, "_clears"):
                self._clears = 0
            if self.current_room.room_type not in ("start", "shop", "treasure"):
                self._clears += 1

            boss = (self.current_room.room_type == "boss")
            every_n = 3
            should_offer = boss or (self._clears % every_n == 0)

            if should_offer:
                # reproducible seed selection
                choice_seed = (
                    (int(self.seed) ^ (self.floor * 10007) ^ (self.current_cell * 9176) ^ (self._clears * 131))
                    & 0x7FFFFFFF
                )
                scene = UpgradeSelectScene(self, rng_seed=choice_seed, allow_skip=(not boss), title="CHOOSE UPGRADE")
                scene.manager = self.manager
                self.manager.switch(scene)
                return

        self._pickup_interactions()
        self._apply_enemy_contact_damage()

        for b in self.current_room.enemy_bullets:
            if b.alive and b.rect.colliderect(self.player.rect):
                self.player.take_damage(b.damage)
                b.alive = False

        hitboxes = self.player.get_melee_hitboxes()
        if hitboxes:
            swing_id = self.player.weapon.swing_id
            dmg = self.player.weapon.damage

            kb_dir = pygame.Vector2(self.player.attack_dir)
            if kb_dir.length_squared() == 0:
                kb_dir = pygame.Vector2(0, 1)
            kb_dir = kb_dir.normalize()

            for e in self.current_room.enemies:
                if not getattr(e, "alive", True):
                    continue
                if any(hb.colliderect(e.rect) for hb in hitboxes):
                    e.take_melee_hit(dmg, swing_id)
                    if self.player.weapon.weapon_id == "bat" and hasattr(e, "apply_knockback"):
                        e.apply_knockback(kb_dir, self.player.weapon.knockback, self.player.weapon.knockback_time)

            for o in self.current_room.objects:
                for hb in hitboxes:
                    if isinstance(o, Crate) and o.alive and hb.colliderect(o.rect):
                        o.take_damage(dmg)
                        break
                    if isinstance(o, Rock) and o.alive and hb.colliderect(o.rect):
                        if self.player.weapon.can_break_walls:
                            o.take_damage(dmg)
                        break

        self._ensure_portal_after_boss()
        self._portal_interaction()

        self._update_feedback_sfx()

        hp_now = int(getattr(self.player, "hp", 0))
        if hp_now < self._prev_hp:
            AUDIO.play_sfx("hurt", channel=AudioManager.CH_PLAYER)
        self._prev_hp = hp_now

    def draw(self, screen):
        screen.fill((0, 0, 0))

        #  PNG
        if not hasattr(self, "_walls_bg"):
            self._walls_bg = pygame.image.load(settings.ROOM_WALLS_PNG).convert_alpha()
        walls = pygame.transform.smoothscale(self._walls_bg, (settings.SCREEN_W, settings.SCREEN_H))
        screen.blit(walls, (0, 0))

        # Next, the room itself is drawn (floor, objects, enemies)
        self.current_room.draw(screen)
        self.current_room.draw_doors(
            screen,
            top=self._has_neighbor(0, -1),
            bottom=self._has_neighbor(0, 1),
            left=self._has_neighbor(-1, 0),
            right=self._has_neighbor(1, 0),
            opened=self.current_room.is_cleared(),
        )

        for s in self.artillery_shells:
            s.draw(screen)
        for p in self.projectiles:
            p.draw(screen)
        for fx in self.effects:
            fx.draw(screen)

        self._draw_portal(screen)
        self.player.draw(screen)

        self.hud.draw(
            screen,
            self.player,
            enemies_count=len(self.current_room.enemies),
            room_type=self.current_room.room_type,
            seed=self.seed,
            floor=self.floor,
        )

        self.minimap.draw(
            screen,
            rooms=self.rooms,
            room_types=self.room_types,
            visited=self.visited_cells,
            current_cell=self.current_cell,
        )


def make_game_scene() -> GameScene:
    return GameScene()


def make_main_menu() -> MainMenuScene:
    return MainMenuScene(make_game_scene=make_game_scene)


def _apply_video_mode() -> pygame.Surface:
    flags = 0
    if APP.fullscreen:
        flags |= pygame.FULLSCREEN
    return pygame.display.set_mode((settings.SCREEN_W, settings.SCREEN_H), flags)


def main():
    pygame.init()

    AUDIO.init()
    AUDIO.load_defaults()

    APP.load()
    apply_audio_from_app(APP)

    screen = _apply_video_mode()
    pygame.display.set_caption("Lab Time Prototype")
    clock = pygame.time.Clock()

    start = make_main_menu()
    manager = SceneManager(start)
    manager.scene.manager = manager

    running = True
    while running:
        dt = clock.tick(settings.FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            manager.scene.handle_event(event)

        if not running:
            break

        pygame.event.pump()

        manager.scene.update(dt)

        if not hasattr(manager.scene, "manager"):
            manager.scene.manager = manager

        if APP.consume_video_dirty():
            screen = _apply_video_mode()

        if APP.consume_audio_dirty():
            apply_audio_from_app(APP)

        manager.scene.draw(screen)
        pygame.display.flip()

    APP.save()
    pygame.quit()


if __name__ == "__main__":
    main()