# ui/hud.py
import pygame
import settings


class HUD:
    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.SysFont("consolas", 18)
        self.font_small = pygame.font.SysFont("consolas", 16)

    def _bar(self, screen, x, y, w, h, ratio, label, color_fg, color_bg=(35, 35, 42)):
        ratio = max(0.0, min(1.0, float(ratio)))
        pygame.draw.rect(screen, color_bg, (x, y, w, h))
        pygame.draw.rect(screen, color_fg, (x, y, int(w * ratio), h))
        pygame.draw.rect(screen, (80, 80, 95), (x, y, w, h), 1)

        txt = self.font_small.render(label, True, (230, 230, 240))
        screen.blit(txt, (x, y - 18))

    def _has_ability(self, player, key: str) -> bool:
        if hasattr(player, "has_ability"):
            return bool(player.has_ability(key))
        # fallback (старый player)
        return True

    def draw(self, screen, player, enemies_count: int, room_type: str, seed: int, floor: int):
        x = 16
        y = 14

        weapon = getattr(getattr(player, "weapon", None), "weapon_id", "club")
        hp = int(getattr(player, "hp", 0))
        max_hp = int(getattr(player, "max_hp", 0))

        line1 = self.font.render(
            f"Floor: {floor}   Seed: {seed}   HP: {hp}/{max_hp}   Weapon: {weapon}   Enemies: {enemies_count}",
            True,
            (235, 235, 245),
        )
        room_line = self.font_small.render(f"Room: {room_type}", True, (210, 210, 220))

        flags = []
        for k in ("Q", "R", "E", "F"):
            flags.append(f"{k}:{'ON' if self._has_ability(player, k) else 'LOCK'}")
        line2 = self.font_small.render("  ".join(flags), True, (200, 200, 210))

        screen.blit(line1, (x, y))
        screen.blit(room_line, (x, y + 22))
        screen.blit(line2, (x, y + 42))

        y2 = y + 76
        w = 220
        h = 12
        gap = 34

        q = getattr(player, "ability_q", None)
        r = getattr(player, "ability_r", None)
        e = getattr(player, "ability_e", None)
        f = getattr(player, "ability_f", None)

        order = [
            ("Q", q, (110, 170, 255)),
            ("R", r, (120, 220, 170)),
            ("E", e, (255, 220, 120)),
            ("F", f, (255, 170, 140)),
        ]

        row = 0
        for key, ab, col in order:
            if ab is None:
                continue
            if not self._has_ability(player, key):
                continue

            yy = y2 + row * gap
            self._bar(
                screen,
                x,
                yy,
                w,
                h,
                ab.cooldown_ratio(),
                f"{key} cd: {max(0.0, float(getattr(ab, 'timer', 0.0))):.2f}s",
                col,
            )
            row += 1