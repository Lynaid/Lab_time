import pygame
import settings


class MapObject:
    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self.alive = True

    def is_solid(self) -> bool:
        return False

    def blocks_projectiles(self) -> bool:
        return self.is_solid()

    def take_damage(self, dmg: int):
        pass

    def update(self, dt: float):
        pass

    def draw(self, screen: pygame.Surface):
        pass


class Rock(MapObject):
    def __init__(self, rect: pygame.Rect):
        super().__init__(rect)
        self.hp = int(settings.ROCK_HP)

    def is_solid(self) -> bool:
        return self.alive

    def blocks_projectiles(self) -> bool:
        return self.alive

    def take_damage(self, dmg: int):
        if not self.alive:
            return
        self.hp -= int(dmg)
        if self.hp <= 0:
            self.alive = False

    def draw(self, screen):
        if not self.alive:
            return
        pygame.draw.rect(screen, settings.ROCK_COLOR, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)


class Crate(MapObject):
    def __init__(self, rect: pygame.Rect):
        super().__init__(rect)
        self.hp = settings.CRATE_HP

    def is_solid(self) -> bool:
        return True

    def take_damage(self, dmg: int):
        if not self.alive:
            return
        self.hp -= int(dmg)
        if self.hp <= 0:
            self.alive = False

    def draw(self, screen):
        if not self.alive:
            return
        pygame.draw.rect(screen, settings.CRATE_COLOR, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)


class Spikes(MapObject):
    def __init__(self, rect: pygame.Rect, damage: int = settings.SPIKES_DAMAGE):
        super().__init__(rect)
        self.damage = int(damage)

    def draw(self, screen):
        pygame.draw.rect(screen, settings.SPIKES_COLOR, self.rect, 2)
        cx, cy = self.rect.center
        pygame.draw.line(screen, settings.SPIKES_COLOR, (self.rect.left, cy), (self.rect.right, cy), 1)
        pygame.draw.line(screen, settings.SPIKES_COLOR, (cx, self.rect.top), (cx, self.rect.bottom), 1)
