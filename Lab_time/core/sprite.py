# core/sprite.py
from __future__ import annotations

from dataclasses import dataclass
import pygame


@dataclass
class AnimDef:
    row: int
    frames: int
    fps: int
    loop: bool = True
    col: int = 0


class SpriteSheet:
    def __init__(self, path: str, frame_w: int, frame_h: int, *, scale: float = 1.0):
        self.path = str(path)
        self.frame_w = int(frame_w)
        self.frame_h = int(frame_h)
        self.scale = float(scale)

        surf = pygame.image.load(self.path).convert_alpha()
        w, h = surf.get_width(), surf.get_height()

        if self.frame_w <= 0 or self.frame_h <= 0:
            raise ValueError(f"[SPRITESHEET INVALID FRAME] {self.path} frame=({self.frame_w},{self.frame_h})")

        if (w % self.frame_w) != 0 or (h % self.frame_h) != 0:
            print("[SPRITESHEET FRAME MISMATCH]")
            print("  file:", self.path)
            print("  image:", (w, h))
            print("  frame:", (self.frame_w, self.frame_h))
            print("  image%frame:", (w % self.frame_w, h % self.frame_h))
            raise ValueError("SpriteSheet frame mismatch")

        self._src = surf
        self.cols = w // self.frame_w
        self.rows = h // self.frame_h

        self.frames: list[list[pygame.Surface]] = []
        for ry in range(self.rows):
            row_frames: list[pygame.Surface] = []
            for cx in range(self.cols):
                r = pygame.Rect(cx * self.frame_w, ry * self.frame_h, self.frame_w, self.frame_h)
                f = surf.subsurface(r).copy()
                if self.scale != 1.0:
                    f = pygame.transform.scale(
                        f,
                        (int(round(self.frame_w * self.scale)), int(round(self.frame_h * self.scale))),
                    )
                row_frames.append(f)
            self.frames.append(row_frames)

    def get(self, row: int, col: int) -> pygame.Surface:
        r = max(0, min(self.rows - 1, int(row)))
        c = max(0, min(self.cols - 1, int(col)))
        return self.frames[r][c]


class SpriteVisual:
    def __init__(
        self,
        sheet: SpriteSheet,
        anims: dict[str, AnimDef],
        *,
        default: str,
        anchor: str = "center",
        offset: tuple[int, int] = (0, 0),
    ):
        self.sheet = sheet
        self.anims = dict(anims)
        self.state = str(default)
        self.anchor = str(anchor)
        self.offset = (int(offset[0]), int(offset[1]))

        self.flip_x = False
        self._t = 0.0
        self._frame_i = 0

    def set_state(self, name: str):
        name = str(name)
        if name == self.state:
            return
        if name not in self.anims:
            return
        self.state = name
        self._t = 0.0
        self._frame_i = 0

    def update(self, dt: float):
        a = self.anims.get(self.state)
        if a is None:
            return
        fps = max(1, int(a.fps))
        frames = max(1, int(a.frames))

        self._t += float(dt)
        step = 1.0 / float(fps)

        while self._t >= step:
            self._t -= step
            self._frame_i += 1
            if self._frame_i >= frames:
                self._frame_i = 0 if a.loop else (frames - 1)

    def _frame_surface(self) -> pygame.Surface:
        a = self.anims.get(self.state)
        if a is None:
            img = self.sheet.get(0, 0)
        else:
            img = self.sheet.get(int(a.row), int(a.col) + int(self._frame_i))
        if self.flip_x:
            img = pygame.transform.flip(img, True, False)
        return img

    def draw(self, screen: pygame.Surface, rect: pygame.Rect, *, debug_hitbox: bool = False):
        img = self._frame_surface()

        if self.anchor == "midbottom":
            x = rect.centerx - img.get_width() // 2
            y = rect.bottom - img.get_height()
        else:
            x = rect.centerx - img.get_width() // 2
            y = rect.centery - img.get_height() // 2

        x += self.offset[0]
        y += self.offset[1]

        screen.blit(img, (int(x), int(y)))

        if debug_hitbox:
            pygame.draw.rect(screen, (0, 255, 255), rect, 1)