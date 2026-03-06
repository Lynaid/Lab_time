import pygame
import settings


class Projectile:
    def __init__(self, pos, direction, damage, piercing=False, trail=False):
        self.pos = pygame.Vector2(pos)
        d = pygame.Vector2(direction)
        if d.length_squared() == 0:
            d = pygame.Vector2(0, 1)
        self.dir = d.normalize()

        self.damage = int(damage)
        self.speed = settings.PROJECTILE_SPEED
        self.ttl = settings.PROJECTILE_TTL
        self.alive = True

        self.piercing = bool(piercing)
        self.trail = bool(trail)
        self.trail_points: list[pygame.Vector2] = []

        s = settings.PROJECTILE_SIZE
        self.rect = pygame.Rect(int(self.pos.x - s/2), int(self.pos.y - s/2), s, s)

    def update(self, dt, solids, bounds):
        if not self.alive:
            return

        if self.trail:
            self.trail_points.append(self.pos.copy())
            if len(self.trail_points) > settings.TRAIL_POINTS:
                self.trail_points.pop(0)

        self.pos += self.dir * self.speed * dt
        self.ttl -= dt

        s = settings.PROJECTILE_SIZE
        self.rect.x = int(self.pos.x - s/2)
        self.rect.y = int(self.pos.y - s/2)

        if self.ttl <= 0:
            self.alive = False
            return

        if not bounds.colliderect(self.rect):
            self.alive = False
            return

        if not self.piercing:
            for r in solids:
                if self.rect.colliderect(r):
                    self.alive = False
                    return

    def draw(self, screen):
        if self.trail and len(self.trail_points) >= 2:
            for p in self.trail_points:
                pygame.draw.circle(screen, settings.TRAIL_COLOR, (int(p.x), int(p.y)), 3)

        pygame.draw.rect(screen, settings.PROJECTILE_COLOR, self.rect)