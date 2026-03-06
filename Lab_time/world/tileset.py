import pygame


class Tiles:
    def __init__(self):

        self.room = pygame.image.load(
            "assets/sprites/room/room_tiles.png"
        ).convert_alpha()

        self.doors = pygame.image.load(
            "assets/sprites/room/Doors.png"
        ).convert_alpha()

        self.rocks = pygame.image.load(
            "assets/sprites/room/Rocks.png"
        ).convert_alpha()

        self.detail = pygame.image.load(
            "assets/sprites/room/Detail.png"
        ).convert_alpha()

        self.size = 32

    def get(self, sheet, x, y):
        s = self.size
        r = pygame.Rect(x*s, y*s, s, s)
        return sheet.subsurface(r)