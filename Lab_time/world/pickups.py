# world/pickups.py
import random
import pygame
import settings


class Pickup:
    """
    kind:
      - random_loot
      - token_upgrade            -> open upgrade menu
      - unlock_r / unlock_e / unlock_f
      - weapon_club / weapon_bat / weapon_hammer
      - heal

    apply(player) -> dict|Pickup|None
      - dict {"action":"upgrade_menu","seed":int}  -> открыть меню улучшений
      - Pickup -> выбросить предмет в мир (оружие)
      - None   -> обычное применение
    """
    def __init__(self, center: tuple[int, int], kind: str):
        s = int(settings.PICKUP_SIZE)
        self.rect = pygame.Rect(0, 0, s, s)
        self.rect.center = (int(center[0]), int(center[1]))
        self.kind = str(kind)
        self.alive = True

    def _choose_random_loot(self, player) -> str:
        run_seed = int(getattr(player, "run_seed", 1))
        rng = random.Random(run_seed ^ (self.rect.centerx << 1) ^ (self.rect.centery << 2) ^ 0xA13F)

        options: list[str] = []

        # abilities unlock first
        if hasattr(player, "has_ability"):
            if not player.has_ability("R"):
                options.append("unlock_r")
            if not player.has_ability("E"):
                options.append("unlock_e")
            if not player.has_ability("F"):
                options.append("unlock_f")

        # upgrade token is always useful
        options.append("token_upgrade")

        # weapons
        wid = getattr(getattr(player, "weapon", None), "weapon_id", "club")
        if wid != "bat":
            options.append("weapon_bat")
        if wid != "hammer":
            options.append("weapon_hammer")

        # fallback
        options.append("heal")

        return rng.choice(options)

    def _spawn_drop_weapon(self, weapon_id: str) -> "Pickup":
        cx, cy = self.rect.center
        return Pickup((cx, cy + int(settings.PICKUP_SIZE) * 2), f"weapon_{weapon_id}")

    def apply(self, player):
        if self.kind == "random_loot":
            self.kind = self._choose_random_loot(player)

        if self.kind == "token_upgrade":
            # seed for reproducible choices
            run_seed = int(getattr(player, "run_seed", 1))
            seed = (run_seed ^ (self.rect.centerx * 9176) ^ (self.rect.centery * 131) ^ 0x55AA) & 0x7FFFFFFF
            return {"action": "upgrade_menu", "seed": int(seed)}

        if self.kind == "unlock_r":
            if hasattr(player, "unlock_ability"):
                player.unlock_ability("R")
            return None

        if self.kind == "unlock_e":
            if hasattr(player, "unlock_ability"):
                player.unlock_ability("E")
            return None

        if self.kind == "unlock_f":
            if hasattr(player, "unlock_ability"):
                player.unlock_ability("F")
            return None

        if self.kind.startswith("weapon_"):
            new_w = self.kind.split("_", 1)[1]
            cur_w = getattr(getattr(player, "weapon", None), "weapon_id", "club")
            if cur_w == new_w:
                return None

            if hasattr(player, "weapon") and hasattr(player.weapon, "set_weapon"):
                player.weapon.set_weapon(new_w)

            return self._spawn_drop_weapon(cur_w)

        if self.kind == "heal":
            if hasattr(player, "heal"):
                player.heal(int(getattr(settings, "REWARD_HEAL", 25)))
            return None

        return None

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return

        pygame.draw.rect(screen, settings.PICKUP_COLOR, self.rect, border_radius=6)
        pygame.draw.rect(screen, settings.PICKUP_OUTLINE, self.rect, 2, border_radius=6)

        font = pygame.font.SysFont("consolas", 18)
        label = {
            "random_loot": "?",
            "token_upgrade": "UP",
            "heal": "HP",
            "unlock_r": "R",
            "unlock_e": "E",
            "unlock_f": "F",
            "weapon_club": "CLB",
            "weapon_bat": "BAT",
            "weapon_hammer": "HAM",
        }.get(self.kind, "?")

        txt = font.render(label, True, (20, 20, 20))
        screen.blit(txt, (self.rect.centerx - txt.get_width() // 2, self.rect.centery - txt.get_height() // 2))