# ui/menus.py
import pygame
import os
import settings
from core.scene import Scene
from audio.audio_manager import AUDIO, AudioManager, apply_audio_from_app
from config.app_config import APP


# -------------------------
# MENU BASE
# -------------------------
class MenuScene(Scene):
    def __init__(self, title: str, options: list[dict]):
        pygame.font.init()
        self.title = str(title)
        self.options = options
        self._logo = None
        self._logo_scaled = None
        self.index = 0
        self.font_title = pygame.font.SysFont("consolas", 48, bold=True)
        self.font = pygame.font.SysFont("consolas", 24)
        self._move_to_first_selectable()

    def _move_to_first_selectable(self):
        for i, opt in enumerate(self.options):
            if opt.get("selectable", True):
                self.index = i
                return
        self.index = 0

    def _move(self, direction: int):
        if not self.options:
            return
        n = len(self.options)
        i = self.index
        for _ in range(n):
            i = (i + direction) % n
            if self.options[i].get("selectable", True):
                self.index = i
                AUDIO.play_ui("move")
                return

    def _activate(self):
        if not self.options:
            return
        opt = self.options[self.index]
        if not opt.get("selectable", True):
            return
        action = opt.get("action", None)
        if callable(action):
            AUDIO.play_ui("select")
            action()

    def _left(self):
        if not self.options:
            return
        opt = self.options[self.index]
        if not opt.get("selectable", True):
            return
        fn = opt.get("left", None)
        if callable(fn):
            AUDIO.play_ui("move")
            fn()

    def _right(self):
        if not self.options:
            return
        opt = self.options[self.index]
        if not opt.get("selectable", True):
            return
        fn = opt.get("right", None)
        if callable(fn):
            AUDIO.play_ui("move")
            fn()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_UP:
            self._move(-1)
        elif event.key == pygame.K_DOWN:
            self._move(+1)
        elif event.key == pygame.K_LEFT:
            self._left()
        elif event.key == pygame.K_RIGHT:
            self._right()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._activate()

    def update(self, dt: float):
        pass

    def draw(self, screen: pygame.Surface):
        screen.fill(settings.BG_COLOR)
        title_surf = self.font_title.render(self.title, True, (245, 245, 255))
        screen.blit(title_surf, ((screen.get_width() - title_surf.get_width()) // 2, 120))
        logo = pygame.image.load("assets/ui/logo.png").convert_alpha()
        logo = pygame.transform.scale(logo, (178, 179))
        screen.blit(logo, (12, 12))

        # text under logo
        font_small = pygame.font.SysFont("consolas", 18)
        tagline = font_small.render("Wij lanceren je de toekomst in!", True, (230, 230, 240))
        screen.blit(tagline, (12, 12 + logo.get_height() + 6))

        start_y = 240
        for i, opt in enumerate(self.options):
            label = opt.get("label", "")
            selectable = opt.get("selectable", True)
            if not selectable:
                color = (170, 170, 190)
            else:
                color = (255, 200, 80) if i == self.index else (230, 230, 240)
            surf = self.font.render(label, True, color)
            screen.blit(surf, ((screen.get_width() - surf.get_width()) // 2, start_y + i * 40))


# -------------------------
# SETTINGS MENU
# -------------------------
class SettingsScene(MenuScene):
    def __init__(self, return_scene: Scene):
        self.return_scene = return_scene
        super().__init__(
            "SETTINGS",
            [
                {"label": "", "action": self._toggle_fullscreen, "selectable": True},
                {"label": "", "action": None, "left": lambda: self._step_difficulty(-1), "right": lambda: self._step_difficulty(+1), "selectable": True},
                {"label": "", "action": None, "left": lambda: self._step_volume("master", -0.05), "right": lambda: self._step_volume("master", +0.05), "selectable": True},
                {"label": "", "action": None, "left": lambda: self._step_volume("sfx", -0.05), "right": lambda: self._step_volume("sfx", +0.05), "selectable": True},
                {"label": "", "action": self._toggle_music, "selectable": True},
                {"label": "", "action": None, "left": lambda: self._step_volume("music", -0.05), "right": lambda: self._step_volume("music", +0.05), "selectable": True},
                {"label": "BACK", "action": self._back, "selectable": True},
            ],
        )
        self._refresh_labels()

    def _difficulty_name(self) -> str:
        if APP.difficulty_scale <= 1.0:
            return "NORMAL"
        if APP.difficulty_scale <= 1.25:
            return "HARD"
        return "BRUTAL"

    def _refresh_labels(self):
        fs = "ON" if APP.fullscreen else "OFF"
        self.options[0]["label"] = f"FULLSCREEN: {fs} (ENTER)"
        self.options[1]["label"] = f"DIFFICULTY: {self._difficulty_name()} (LEFT/RIGHT)"
        mv = int(round(APP.master_volume * 100))
        sv = int(round(APP.sfx_volume * 100))
        muv = int(round(APP.music_volume * 100))
        self.options[2]["label"] = f"MASTER VOLUME: {mv}% (LEFT/RIGHT)"
        self.options[3]["label"] = f"SFX VOLUME:    {sv}% (LEFT/RIGHT)"
        me = "ON" if APP.music_enabled else "OFF"
        self.options[4]["label"] = f"MUSIC: {me} (ENTER)"
        self.options[5]["label"] = f"MUSIC VOLUME:  {muv}% (LEFT/RIGHT)"

    def _toggle_fullscreen(self):
        APP.toggle_fullscreen()
        APP.save()
        self._refresh_labels()

    def _step_difficulty(self, direction: int):
        vals = [1.0, 1.25, 1.6]
        cur = APP.difficulty_scale
        idx = 0
        for i, v in enumerate(vals):
            if abs(cur - v) < 1e-6:
                idx = i
                break
        idx = (idx + (1 if direction > 0 else -1)) % len(vals)
        APP.difficulty_scale = vals[idx]
        APP.save()
        self._refresh_labels()

    def _step_volume(self, kind: str, delta: float):
        if kind == "master":
            APP.master_volume = max(0.0, min(1.0, APP.master_volume + delta))
        elif kind == "sfx":
            APP.sfx_volume = max(0.0, min(1.0, APP.sfx_volume + delta))
        else:
            APP.music_volume = max(0.0, min(1.0, APP.music_volume + delta))
        APP.mark_audio_dirty()
        APP.save()
        self._refresh_labels()

    def _toggle_music(self):
        APP.music_enabled = not APP.music_enabled
        APP.mark_audio_dirty()
        APP.save()
        self._refresh_labels()

    def _back(self):
        AUDIO.play_ui("back")
        self.manager.switch(self.return_scene)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()
            return
        super().handle_event(event)


# -------------------------
# CONTROLS
# -------------------------
class ControlsScene(Scene):
    def __init__(self, return_scene: Scene):
        pygame.font.init()
        self.return_scene = return_scene
        self.font_title = pygame.font.SysFont("consolas", 48, bold=True)
        self.font = pygame.font.SysFont("consolas", 22)
        self.lines = [
            "MOVE:          W A S D",
            "AIM:           ARROWS",
            "MELEE:         SPACE",
            "Q:             FAST SHOT",
            "R:             BULLET CYCLE",
            "E:             ATOMIC BLAST",
            "F:             ARTILLERY RAIN",
            "",
            "PAUSE:         ESC",
            "NEXT FLOOR:    ENTER (IN PORTAL)",
            "",
            "DEBUG WEAPON:  1 / 2 / 3",
            "UPGRADES TEST: Z / X / C",
            "",
            "ESC / ENTER - BACK",
        ]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            AUDIO.play_ui("back")
            self.manager.switch(self.return_scene)

    def update(self, dt: float):
        pass

    def draw(self, screen: pygame.Surface):
        screen.fill(settings.BG_COLOR)
        title = self.font_title.render("CONTROLS", True, (245, 245, 255))
        screen.blit(title, ((screen.get_width() - title.get_width()) // 2, 90))
        x, y = 140, 190
        for line in self.lines:
            surf = self.font.render(line, True, (230, 230, 240))
            screen.blit(surf, (x, y))
            y += 30


# -------------------------
# MENUS
# -------------------------
class MainMenuScene(MenuScene):
    def __init__(self, make_game_scene):
        self._make_game_scene = make_game_scene

        def start_game():
            game = self._make_game_scene()
            game.manager = self.manager
            self.manager.switch(game)

        def open_settings():
            s = SettingsScene(return_scene=self)
            s.manager = self.manager
            self.manager.switch(s)

        def open_controls():
            c = ControlsScene(return_scene=self)
            c.manager = self.manager
            self.manager.switch(c)

        def quit_game():
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        def _get_logo(self):
            if self._logo is None:
                path = os.path.join("assets", "ui", "logo.png")
                self._logo = pygame.image.load(path).convert_alpha()
                self._logo_scaled = None
            return self._logo    

        super().__init__(
            "LAB TIME",
            [
                {"label": "START GAME", "action": start_game, "selectable": True},
                {"label": "SETTINGS", "action": open_settings, "selectable": True},
                {"label": "CONTROLS", "action": open_controls, "selectable": True},
                {"label": "QUIT", "action": quit_game, "selectable": True},
            ],
        )

    def update(self, dt: float):
        AUDIO.play_music("menu", loop=True, fade_ms=250)
        AUDIO.set_ambience(None)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return
        super().handle_event(event)


class PauseScene(MenuScene):
    def __init__(self, game_scene, make_game_scene, make_main_menu):
        self.game = game_scene
        self._make_game_scene = make_game_scene
        self._make_main_menu = make_main_menu

        def resume():
            AUDIO.play_sfx("resume", channel=AudioManager.CH_UI)
            self.manager.switch(self.game)

        def open_settings():
            s = SettingsScene(return_scene=self)
            s.manager = self.manager
            self.manager.switch(s)

        def open_controls():
            c = ControlsScene(return_scene=self)
            c.manager = self.manager
            self.manager.switch(c)

        def restart():
            game = self._make_game_scene()
            game.manager = self.manager
            self.manager.switch(game)

        def main_menu():
            menu = self._make_main_menu()
            menu.manager = self.manager
            self.manager.switch(menu)

        def quit_game():
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        super().__init__(
            "PAUSED",
            [
                {"label": "RESUME", "action": resume, "selectable": True},
                {"label": "SETTINGS", "action": open_settings, "selectable": True},
                {"label": "CONTROLS", "action": open_controls, "selectable": True},
                {"label": "RESTART", "action": restart, "selectable": True},
                {"label": "MAIN MENU", "action": main_menu, "selectable": True},
                {"label": "QUIT", "action": quit_game, "selectable": True},
            ],
        )
        AUDIO.play_sfx("pause", channel=AudioManager.CH_UI)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            AUDIO.play_sfx("resume", channel=AudioManager.CH_UI)
            self.manager.switch(self.game)
            return
        super().handle_event(event)

    def draw(self, screen: pygame.Surface):
        self.game.draw(screen)
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        super().draw(screen)


class GameOverScene(MenuScene):
    def __init__(self, floor: int, seed: int, make_game_scene, make_main_menu):
        self.floor = int(floor)
        self.seed = int(seed)
        self._make_game_scene = make_game_scene
        self._make_main_menu = make_main_menu

        def restart():
            game = self._make_game_scene()
            game.manager = self.manager
            self.manager.switch(game)

        def main_menu():
            menu = self._make_main_menu()
            menu.manager = self.manager
            self.manager.switch(menu)

        def quit_game():
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        super().__init__(
            "GAME OVER",
            [
                {"label": f"FLOOR: {self.floor}", "action": None, "selectable": False},
                {"label": f"SEED : {self.seed}", "action": None, "selectable": False},
                {"label": "RESTART", "action": restart, "selectable": True},
                {"label": "MAIN MENU", "action": main_menu, "selectable": True},
                {"label": "QUIT", "action": quit_game, "selectable": True},
            ],
        )
        AUDIO.play_sfx("game_over", channel=AudioManager.CH_UI)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return
        super().handle_event(event)
