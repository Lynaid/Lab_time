# ui/minimap.py
import pygame
import settings


class MiniMap:
    def __init__(self):
        pass

    def draw(
        self,
        screen,
        rooms: dict[int, object],
        room_types: dict[int, str],
        visited: set[int],
        current_cell: int,
    ):
        cell_size = settings.MINIMAP_CELL
        gap = settings.MINIMAP_GAP
        ox = settings.MINIMAP_X
        oy = settings.MINIMAP_Y

        w = settings.MAP_W * cell_size + (settings.MAP_W - 1) * gap + 16
        h = settings.MAP_H * cell_size + (settings.MAP_H - 1) * gap + 16

        pygame.draw.rect(screen, settings.MINIMAP_COLOR_BG, (ox - 8, oy - 8, w, h))
        pygame.draw.rect(screen, settings.MINIMAP_COLOR_BORDER, (ox - 8, oy - 8, w, h), 1)

        mw = int(settings.MAP_W)

        # visited + current
        for cell in visited | {current_cell}:
            if cell not in rooms:
                continue

            x = cell % mw
            y = cell // mw

            px = ox + x * (cell_size + gap)
            py = oy + y * (cell_size + gap)

            rtype = room_types.get(cell, "normal")
            color = settings.MINIMAP_TYPE_COLORS.get(rtype, settings.MINIMAP_COLOR_VISITED)

            pygame.draw.rect(screen, color, (px, py, cell_size, cell_size))
            pygame.draw.rect(screen, (0, 0, 0), (px, py, cell_size, cell_size), 1)

        cx = current_cell % mw
        cy = current_cell // mw

        px = ox + cx * (cell_size + gap)
        py = oy + cy * (cell_size + gap)

        pygame.draw.rect(
            screen,
            settings.MINIMAP_COLOR_CURRENT,
            (px - 2, py - 2, cell_size + 4, cell_size + 4),
            2
        )