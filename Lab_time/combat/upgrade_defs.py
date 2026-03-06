# combat/upgrade_defs.py
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class UpgradeDef:
    id: str
    name: str
    desc: str
    can_offer: Callable[[object], bool]
    apply: Callable[[object], None]


def ALL_UPGRADES() -> list[UpgradeDef]:
    ups: list[UpgradeDef] = []

    # ---------- Q ----------
    ups.append(UpgradeDef(
        id="Q_IMPROVED",
        name="Q: Improved Shot",
        desc="Piercing + trail (settings improved).",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: True)("Q") and not p.ability_q.improved,
        apply=lambda p: setattr(p.ability_q, "improved", True),
    ))

    ups.append(UpgradeDef(
        id="Q_DMG_2",
        name="Q: Damage +2",
        desc="Q damage +2 permanently.",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: True)("Q"),
        apply=lambda p: setattr(p.ability_q, "bonus_damage", int(getattr(p.ability_q, "bonus_damage", 0)) + 2),
    ))

    ups.append(UpgradeDef(
        id="Q_CD_15",
        name="Q: Cooldown -15%",
        desc="Q cooldown faster.",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: True)("Q"),
        apply=lambda p: setattr(p.ability_q, "cooldown_mult", float(getattr(p.ability_q, "cooldown_mult", 1.0)) * 0.85),
    ))

    # ---------- R ----------
    ups.append(UpgradeDef(
        id="R_STORM",
        name="R: Storm",
        desc="R uses storm parameters (settings).",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("R") and not p.ability_r.storm,
        apply=lambda p: setattr(p.ability_r, "storm", True),
    ))

    ups.append(UpgradeDef(
        id="R_COUNT_2",
        name="R: +2 Bullets",
        desc="R burst +2 bullets.",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("R"),
        apply=lambda p: setattr(p.ability_r, "bonus_count", int(getattr(p.ability_r, "bonus_count", 0)) + 2),
    ))

    ups.append(UpgradeDef(
        id="R_INTERVAL_10",
        name="R: Fire Rate +10%",
        desc="R interval *0.90 (faster).",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("R"),
        apply=lambda p: setattr(p.ability_r, "interval_mult", float(getattr(p.ability_r, "interval_mult", 1.0)) * 0.90),
    ))

    ups.append(UpgradeDef(
        id="R_CD_15",
        name="R: Cooldown -15%",
        desc="R cooldown faster.",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("R"),
        apply=lambda p: setattr(p.ability_r, "cooldown_mult", float(getattr(p.ability_r, "cooldown_mult", 1.0)) * 0.85),
    ))

    # ---------- E ----------
    ups.append(UpgradeDef(
        id="E_RADIUS_24",
        name="E: Radius +24",
        desc="Explosion bigger.",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("E"),
        apply=lambda p: setattr(p.ability_e, "bonus_radius", float(getattr(p.ability_e, "bonus_radius", 0.0)) + 24.0),
    ))

    ups.append(UpgradeDef(
        id="E_DMG_3",
        name="E: Damage +3",
        desc="Explosion damage +3.",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("E"),
        apply=lambda p: setattr(p.ability_e, "bonus_damage", int(getattr(p.ability_e, "bonus_damage", 0)) + 3),
    ))

    ups.append(UpgradeDef(
        id="E_CD_15",
        name="E: Cooldown -15%",
        desc="E cooldown faster.",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("E"),
        apply=lambda p: setattr(p.ability_e, "cooldown_mult", float(getattr(p.ability_e, "cooldown_mult", 1.0)) * 0.85),
    ))

    # ---------- F ----------
    ups.append(UpgradeDef(
        id="F_BIG",
        name="F: Big Salvo",
        desc="Unlock big salvo mode (settings).",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("F") and not p.ability_f.big_salvo,
        apply=lambda p: setattr(p.ability_f, "big_salvo", True),
    ))

    ups.append(UpgradeDef(
        id="F_SHELLS_2",
        name="F: +2 Shells",
        desc="Normal F +2 shells.",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("F"),
        apply=lambda p: setattr(p.ability_f, "bonus_shells", int(getattr(p.ability_f, "bonus_shells", 0)) + 2),
    ))

    ups.append(UpgradeDef(
        id="F_DMG_2",
        name="F: Damage +2",
        desc="Normal F shell damage +2.",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("F"),
        apply=lambda p: setattr(p.ability_f, "bonus_damage", int(getattr(p.ability_f, "bonus_damage", 0)) + 2),
    ))

    ups.append(UpgradeDef(
        id="F_CD_15",
        name="F: Cooldown -15%",
        desc="F cooldown faster.",
        can_offer=lambda p: getattr(p, "has_ability", lambda k: False)("F"),
        apply=lambda p: setattr(p.ability_f, "cooldown_mult", float(getattr(p.ability_f, "cooldown_mult", 1.0)) * 0.85),
    ))

    # ---------- GLOBAL ----------
    ups.append(UpgradeDef(
        id="G_MAXHP_1",
        name="Max HP +1",
        desc="Max HP +1 and heal +1.",
        can_offer=lambda p: True,
        apply=lambda p: (setattr(p, "max_hp", int(p.max_hp) + 1), setattr(p, "hp", min(int(p.max_hp), int(p.hp) + 1))),
    ))

    ups.append(UpgradeDef(
        id="G_SPEED_20",
        name="Move Speed +20",
        desc="Movement speed bonus +20.",
        can_offer=lambda p: True,
        apply=lambda p: setattr(p, "move_speed_bonus", float(getattr(p, "move_speed_bonus", 0.0)) + 20.0),
    ))

    ups.append(UpgradeDef(
        id="G_MELEE_DMG_1",
        name="Melee Damage +1",
        desc="Melee weapon damage +1.",
        can_offer=lambda p: hasattr(p, "weapon"),
        apply=lambda p: setattr(p.weapon, "damage", int(getattr(p.weapon, "damage", 1)) + 1),
    ))

    return ups
