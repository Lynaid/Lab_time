# ui/upgrade_menu.py
import pygame
import settings

from core.scene import Scene
from audio.audio_manager import AUDIO
from combat.upgrades import pick_upgrade_choices


class UpgradeSelectScene(Scene):
    """
    Простое меню выбора улучшения (3 карточки).
    Управление:
      ←/→ или A/D — выбор
      ENTER/SPACE — принять
      ESC — пропустить (если allow_skip=True)
    """
    def __init__(
        self,
        game_scene,
        *,
        rng_seed: int,
        allow_skip: bool = True,
        title: str = "CHOOSE UPGRADE",
    ):
        self.game_scene = game_scene
        self.allow_skip = bool(allow_skip)
        self.title = str(title)

        self._font = pygame.font.SysFont("consolas", 28)
        self._font_small = pygame.font.SysFont("consolas", 18)

        # выбор 3 апгрейдов с учётом уже взятых
        self.choices = pick_upgrade_choices(
            player=self.game_scene.player,
            seed=int(rng_seed),
            k=3
        )
        self.index = 0

        # если выбора нет — сразу выходим
        if not self.choices:
            self._return_to_game()

    def _return_to_game(self):
        self.manager.switch(self.game_scene)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_LEFT, pygame.K_a):
            self.index = (self.index - 1) % len(self.choices)
            AUDIO.play_ui("move")
            return

        if event.key in (pygame.K_RIGHT, pygame.K_d):
            self.index = (self.index + 1) % len(self.choices)
            AUDIO.play_ui("move")
            return

        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            up = self.choices[self.index]
            self.game_scene.player.upgrades.add(up, self.game_scene.player)
            AUDIO.play_ui("select")
            self._return_to_game()
            return

        if event.key == pygame.K_ESCAPE and self.allow_skip:
            AUDIO.play_ui("back")
            self._return_to_game()
            return

    def update(self, dt: float):
        # ничего не симулируем, только UI
        pass

    def draw(self, screen):
        # рисуем “замороженный” кадр игры
        self.game_scene.draw(screen)

        # затемнение
        overlay = pygame.Surface((settings.SCREEN_W, settings.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        # заголовок
        title = self._font.render(self.title, True, (240, 240, 250))
        screen.blit(title, (settings.SCREEN_W // 2 - title.get_width() // 2, 70))

        # карточки
        w = 300
        h = 170
        gap = 40
        total = len(self.choices) * w + (len(self.choices) - 1) * gap
        start_x = settings.SCREEN_W // 2 - total // 2
        y = settings.SCREEN_H // 2 - h // 2

        for i, up in enumerate(self.choices):
            x = start_x + i * (w + gap)
            r = pygame.Rect(x, y, w, h)

            selected = (i == self.index)
            bg = (230, 230, 245) if selected else (170, 170, 190)
            border = (30, 30, 40) if selected else (10, 10, 15)

            pygame.draw.rect(screen, bg, r, border_radius=14)
            pygame.draw.rect(screen, border, r, 3, border_radius=14)

            name = self._font_small.render(up.name, True, (20, 20, 26))
            screen.blit(name, (r.centerx - name.get_width() // 2, r.y + 18))

            # описание (2 строки максимум)
            desc_lines = up.description.split("\n")[:2]
            yy = r.y + 60
            for line in desc_lines:
                t = self._font_small.render(line, True, (25, 25, 32))
                screen.blit(t, (r.centerx - t.get_width() // 2, yy))
                yy += 22

        # подсказки
        hint = "LEFT/RIGHT — choose   ENTER — take"
        if self.allow_skip:
            hint += "   ESC — skip"
        t = self._font_small.render(hint, True, (240, 240, 250))
        screen.blit(t, (settings.SCREEN_W // 2 - t.get_width() // 2, settings.SCREEN_H - 90))
