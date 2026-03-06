# world/map_gen.py
import random
from collections import deque
import settings


# --- Helpers: grid navigation ---

def _dirs():
    w = int(settings.MAP_W)
    return {"U": -w, "D": +w, "L": -1, "R": +1}

def _cell_xy(cell: int):
    w = int(settings.MAP_W)
    return cell % w, cell // w

def _xy_cell(x: int, y: int) -> int:
    w = int(settings.MAP_W)
    return y * w + x

def _in_bounds(cell: int) -> bool:
    x, y = _cell_xy(cell)
    return 0 <= x < int(settings.MAP_W) and 0 <= y < int(settings.MAP_H)

def _neighbors(cell: int):
    dirs = _dirs()
    for d in dirs.values():
        n = cell + d
        if _in_bounds(n):
            yield n


# --- Helpers: graph analysis ---

def _degree(cell: int, rooms: set[int]) -> int:
    return sum(1 for n in _neighbors(cell) if n in rooms)

def _bfs_distances(start: int, rooms: set[int]) -> dict[int, int]:
    dist = {start: 0}
    q = deque([start])
    while q:
        cur = q.popleft()
        for n in _neighbors(cur):
            if n in rooms and n not in dist:
                dist[n] = dist[cur] + 1
                q.append(n)
    return dist

def _safe_start_cell() -> int:
    start = int(getattr(settings, "START_CELL", 0))
    if _in_bounds(start):
        return start
    cx = int(settings.MAP_W) // 2
    cy = int(settings.MAP_H) // 2
    return _xy_cell(cx, cy)


# --- Main generation ---

def generate_rooms(seed: int | None = None):

    # Seed & init
    if seed is None:
        seed = random.randrange(1, 2_147_483_647)
    rng = random.Random(seed)
    start = _safe_start_cell()
    target = rng.randint(int(settings.ROOMS_MIN), int(settings.ROOMS_MAX))

    # Random walk to build room set
    rooms: set[int] = {start}
    dirs = list(_dirs().values())
    attempts = 0
    while len(rooms) < target and attempts < 5000:
        attempts += 1
        base = rng.choice(tuple(rooms))
        d = rng.choice(dirs)
        new = base + d
        if not _in_bounds(new):
            continue
        if new in rooms:
            continue
        if _degree(new, rooms) <= 1:
            rooms.add(new)

    # Assign base types
    room_types: dict[int, str] = {cell: "normal" for cell in rooms}
    room_types[start] = "start"

    # Place special rooms at dead ends
    dist = _bfs_distances(start, rooms)
    dead_ends = [c for c in rooms if _degree(c, rooms) == 1 and c != start]

    boss = max(dead_ends, key=lambda c: dist.get(c, 0))
    room_types[boss] = "boss"
    dead_ends.remove(boss)

    rng.shuffle(dead_ends)
    if dead_ends:
        room_types[dead_ends[0]] = "treasure"
    if len(dead_ends) > 1:
        room_types[dead_ends[1]] = "shop"

    # Secret room: empty cell with 3+ room neighbors
    secret_candidates = []
    for y in range(int(settings.MAP_H)):
        for x in range(int(settings.MAP_W)):
            cell = _xy_cell(x, y)
            if cell in rooms:
                continue
            if sum(1 for n in _neighbors(cell) if n in rooms) >= 3:
                secret_candidates.append(cell)

    if secret_candidates:
        secret = rng.choice(secret_candidates)
        room_types[secret] = "secret"
        rooms.add(secret)

    return rooms, room_types, seed