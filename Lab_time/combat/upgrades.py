# combat/upgrades.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import random


@dataclass(frozen=True)
class Upgrade:
    id: str
    target: str
    tags: frozenset[str]
    name: str
    description: str
    apply: Callable[[object], None]
    tier: int = 1
    weight: int = 10


class UpgradeManager:
    def __init__(self):
        self.active: dict[str, Upgrade] = {}

    def has(self, uid: str) -> bool:
        return str(uid) in self.active

    def add(self, upgrade: Upgrade, player) -> bool:
        uid = str(upgrade.id)
        if uid in self.active:
            return False
        self.active[uid] = upgrade
        upgrade.apply(player)
        return True

    def list_ids(self) -> list[str]:
        return list(self.active.keys())


# -------------------------
# helpers (safe set)
# -------------------------
def _set(obj, name: str, value):
    try:
        setattr(obj, name, value)
    except Exception:
        pass


def _get(obj, name: str, default):
    try:
        return getattr(obj, name)
    except Exception:
        return default


# -------------------------
# Upgrade pool (MATCHES combat/abilities.py)
# -------------------------
def _pool() -> list[Upgrade]:
    ups: list[Upgrade] = []

    # ---------- Q ----------
    def q_improved(player):
        # abilities.FastShot uses: improved
        _set(player.ability_q, "improved", True)

    ups.append(Upgrade(
        id="Q_IMPROVED",
        target="Q",
        tags=frozenset({"q", "improved"}),
        name="Q: Improved",
        description="Switch Q to improved mode.",
        apply=q_improved
    ))

    def q_piercing(player):
        # abilities.FastShot uses: force_piercing
        _set(player.ability_q, "force_piercing", True)
        # alias for older code (safe)
        _set(player.ability_q, "piercing", True)

    ups.append(Upgrade(
        id="Q_PIERCING",
        target="Q",
        tags=frozenset({"q", "piercing"}),
        name="Q: Piercing",
        description="Q bullets pierce enemies.",
        apply=q_piercing
    ))

    def q_trail(player):
        # abilities.FastShot uses: force_trail
        _set(player.ability_q, "force_trail", True)
        # alias for older code (safe)
        _set(player.ability_q, "trail", True)

    ups.append(Upgrade(
        id="Q_TRAIL",
        target="Q",
        tags=frozenset({"q", "trail"}),
        name="Q: Trail",
        description="Q leaves trail (if supported).",
        apply=q_trail
    ))

    def q_damage_plus(player):
        cur = int(_get(player.ability_q, "bonus_damage", 0))
        _set(player.ability_q, "bonus_damage", cur + 2)

    ups.append(Upgrade(
        id="Q_DAMAGE_PLUS",
        target="Q",
        tags=frozenset({"q", "damage"}),
        name="Q: Damage +2",
        description="Q damage +2.",
        apply=q_damage_plus
    ))

    def q_cd_minus(player):
        cur = float(_get(player.ability_q, "cooldown_mult", 1.0))
        _set(player.ability_q, "cooldown_mult", cur * 0.85)

    ups.append(Upgrade(
        id="Q_CD_15",
        target="Q",
        tags=frozenset({"q", "cooldown"}),
        name="Q: Cooldown -15%",
        description="Q cooldown faster.",
        apply=q_cd_minus
    ))

    # ---------- R ----------
    def r_storm(player):
        # abilities.BulletCycle uses: storm
        _set(player.ability_r, "storm", True)
        # alias (safe)
        _set(player.ability_r, "storm_mode", True)

    ups.append(Upgrade(
        id="R_STORM",
        target="R",
        tags=frozenset({"r", "storm"}),
        name="R: Storm",
        description="R becomes storm mode.",
        apply=r_storm
    ))

    def r_count_plus(player):
        cur = int(_get(player.ability_r, "bonus_count", 0))
        _set(player.ability_r, "bonus_count", cur + 2)
        # alias (safe)
        cur2 = int(_get(player.ability_r, "queue_bonus", 0))
        _set(player.ability_r, "queue_bonus", cur2 + 2)

    ups.append(Upgrade(
        id="R_COUNT_PLUS",
        target="R",
        tags=frozenset({"r", "count"}),
        name="R: +2 bullets",
        description="R burst +2 bullets.",
        apply=r_count_plus
    ))

    def r_damage_plus(player):
        cur = int(_get(player.ability_r, "bonus_damage", 0))
        _set(player.ability_r, "bonus_damage", cur + 1)

    ups.append(Upgrade(
        id="R_DAMAGE_PLUS",
        target="R",
        tags=frozenset({"r", "damage"}),
        name="R: Damage +1",
        description="R bullets damage +1.",
        apply=r_damage_plus
    ))

    def r_fire_rate(player):
        cur = float(_get(player.ability_r, "interval_mult", 1.0))
        _set(player.ability_r, "interval_mult", cur * 0.90)

    ups.append(Upgrade(
        id="R_FIRE_10",
        target="R",
        tags=frozenset({"r", "rate"}),
        name="R: Fire rate +10%",
        description="R interval *0.90.",
        apply=r_fire_rate
    ))

    def r_cd_minus(player):
        cur = float(_get(player.ability_r, "cooldown_mult", 1.0))
        _set(player.ability_r, "cooldown_mult", cur * 0.85)

    ups.append(Upgrade(
        id="R_CD_15",
        target="R",
        tags=frozenset({"r", "cooldown"}),
        name="R: Cooldown -15%",
        description="R cooldown faster.",
        apply=r_cd_minus
    ))

    # ---------- E ----------
    def e_radius_plus(player):
        cur = float(_get(player.ability_e, "bonus_radius", 0.0))
        _set(player.ability_e, "bonus_radius", cur + 24.0)
        # alias (safe)
        cur2 = float(_get(player.ability_e, "radius_bonus", 0.0))
        _set(player.ability_e, "radius_bonus", cur2 + 24.0)

    ups.append(Upgrade(
        id="E_RADIUS_PLUS",
        target="E",
        tags=frozenset({"e", "radius"}),
        name="E: Radius +24",
        description="E radius +24.",
        apply=e_radius_plus
    ))

    def e_damage_plus(player):
        cur = int(_get(player.ability_e, "bonus_damage", 0))
        _set(player.ability_e, "bonus_damage", cur + 3)

    ups.append(Upgrade(
        id="E_DAMAGE_PLUS",
        target="E",
        tags=frozenset({"e", "damage"}),
        name="E: Damage +3",
        description="E damage +3.",
        apply=e_damage_plus
    ))

    def e_cd_minus(player):
        cur = float(_get(player.ability_e, "cooldown_mult", 1.0))
        _set(player.ability_e, "cooldown_mult", cur * 0.85)

    ups.append(Upgrade(
        id="E_CD_15",
        target="E",
        tags=frozenset({"e", "cooldown"}),
        name="E: Cooldown -15%",
        description="E cooldown faster.",
        apply=e_cd_minus
    ))

    # ---------- F ----------
    def f_big_salvo(player):
        # abilities.ArtilleryRain uses: big_salvo
        _set(player.ability_f, "big_salvo", True)
        # alias (safe)
        _set(player.ability_f, "big_salvo_mode", True)

    ups.append(Upgrade(
        id="F_BIG_SALVO",
        target="F",
        tags=frozenset({"f", "big"}),
        name="F: Big Salvo",
        description="F big salvo mode.",
        apply=f_big_salvo
    ))

    def f_shells_plus(player):
        cur = int(_get(player.ability_f, "bonus_shells", 0))
        _set(player.ability_f, "bonus_shells", cur + 2)
        # alias (safe)
        cur2 = int(_get(player.ability_f, "count_bonus", 0))
        _set(player.ability_f, "count_bonus", cur2 + 2)

    ups.append(Upgrade(
        id="F_SHELLS_PLUS",
        target="F",
        tags=frozenset({"f", "shells"}),
        name="F: +2 shells",
        description="Normal F +2 shells.",
        apply=f_shells_plus
    ))

    def f_damage_plus(player):
        cur = int(_get(player.ability_f, "bonus_damage", 0))
        _set(player.ability_f, "bonus_damage", cur + 2)

    ups.append(Upgrade(
        id="F_DAMAGE_PLUS",
        target="F",
        tags=frozenset({"f", "damage"}),
        name="F: Damage +2",
        description="Normal F damage +2.",
        apply=f_damage_plus
    ))

    def f_cd_minus(player):
        cur = float(_get(player.ability_f, "cooldown_mult", 1.0))
        _set(player.ability_f, "cooldown_mult", cur * 0.85)

    ups.append(Upgrade(
        id="F_CD_15",
        target="F",
        tags=frozenset({"f", "cooldown"}),
        name="F: Cooldown -15%",
        description="F cooldown faster.",
        apply=f_cd_minus
    ))

    # ---------- GLOBAL ----------
    def g_maxhp(player):
        player.max_hp += 1
        player.hp = min(player.max_hp, player.hp + 1)

    ups.append(Upgrade(
        id="G_MAXHP_1",
        target="GLOBAL",
        tags=frozenset({"global", "hp"}),
        name="Max HP +1",
        description="Max HP +1 and heal +1.",
        apply=g_maxhp
    ))

    def g_speed(player):
        cur = float(_get(player, "move_speed_bonus", 0.0))
        _set(player, "move_speed_bonus", cur + 20.0)

    ups.append(Upgrade(
        id="G_SPEED_20",
        target="GLOBAL",
        tags=frozenset({"global", "speed"}),
        name="Move Speed +20",
        description="Movement speed +20.",
        apply=g_speed
    ))

    def g_melee_dmg(player):
        w = getattr(player, "weapon", None)
        if w is None:
            return
        dmg = int(_get(w, "damage", 1))
        _set(w, "damage", dmg + 1)

    ups.append(Upgrade(
        id="G_MELEE_DMG_1",
        target="GLOBAL",
        tags=frozenset({"global", "melee"}),
        name="Melee Damage +1",
        description="Melee damage +1.",
        apply=g_melee_dmg
    ))

    return ups


def pick_upgrade_choices(player, seed: int, k: int = 3):
    rng = random.Random(int(seed))

    pool = [u for u in _pool() if not player.upgrades.has(u.id)]

    weighted = []
    for up in pool:
        weighted.extend([up] * max(1, int(up.weight)))

    rng.shuffle(weighted)

    result = []
    used = set()

    for up in weighted:
        if up.id in used:
            continue
        result.append(up)
        used.add(up.id)
        if len(result) >= k:
            break

    return result