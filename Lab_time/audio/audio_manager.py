# audio/audio_manager.py
import os
import random
import pygame


class AudioManager:
    """
    Audio routing:
      CH_UI       = 0  (UI blips)
      CH_PLAYER   = 1  (player one-shots)
      CH_AMBIENCE = 2  (loop ambience only)
      CH_WORLD    = 3  (world one-shots; optional, can also use play_sfx_world_at)
    """
    CH_UI = 0
    CH_PLAYER = 1
    CH_AMBIENCE = 2
    CH_WORLD = 3

    def __init__(self):
        self.enabled = False

        # banks
        self.ui: dict[str, list[pygame.mixer.Sound] | None] = {}
        self.sfx: dict[str, list[pygame.mixer.Sound] | None] = {}

        # path maps
        self.ambience: dict[str, str | None] = {}
        self.music_tracks: dict[str, str | None] = {}

        self._current_music_key: str | None = None
        self._current_ambience_key: str | None = None

        # volumes (public)
        self.master_volume = 0.8
        self.sfx_volume = 0.8
        self.music_volume = 0.6
        self.music_enabled = True

        # cached clamped vols
        self._mv = 0.8
        self._sv = 0.8
        self._musv = 0.6

        # cooldown spam guard
        self._cooldowns: dict[str, float] = {}
        self._last_play_time: dict[str, float] = {}

        # paths
        self._base_dir = os.path.dirname(os.path.abspath(__file__))  # .../audio
        self._project_dir = os.path.dirname(self._base_dir)          # project root

        self._assets_dir = os.path.join(self._project_dir, "assets")
        self._sfx_dir = os.path.join(self._assets_dir, "sfx")
        self._music_dir = os.path.join(self._assets_dir, "music")
        self._amb_dir = os.path.join(self._assets_dir, "ambience")

    # -------------------------
    # init / load
    # -------------------------
    def init(self):
        """
        Safe mixer init with sane defaults.
        Important: set_num_channels AFTER init.
        """
        try:
            if not pygame.mixer.get_init():
                # Prefer explicit init (stable defaults)
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
            pygame.mixer.set_num_channels(16)
            # Ensure channels exist and can be configured
            self.apply_volumes()
        except Exception:
            self.enabled = False

    def _try_load_sound(self, path: str):
        if not self.enabled:
            return None
        if not os.path.exists(path):
            return None
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            return None

    def _load_variants(self, stem: str, exts=(".wav", ".ogg")):
        """
        Loads:
          sfx/stem.wav|ogg
          sfx/stem_1.wav|ogg ... stem_9.wav|ogg
        Returns list[Sound] or None.
        """
        if not self.enabled:
            return None

        sounds: list[pygame.mixer.Sound] = []

        # stem.ext (single)
        for ext in exts:
            p = os.path.join(self._sfx_dir, stem + ext)
            s = self._try_load_sound(p)
            if s is not None:
                sounds.append(s)
                break

        # stem_1.ext ... stem_9.ext
        for i in range(1, 10):
            found_any = False
            for ext in exts:
                p = os.path.join(self._sfx_dir, f"{stem}_{i}{ext}")
                s = self._try_load_sound(p)
                if s is not None:
                    sounds.append(s)
                    found_any = True
                    break
            if not found_any:
                break

        return sounds if sounds else None

    def _find_music_file(self, stem: str):
        for ext in (".ogg", ".mp3", ".wav"):
            p = os.path.join(self._music_dir, stem + ext)
            if os.path.exists(p):
                return p
        return None

    def _find_ambience_file(self, stem: str):
        for ext in (".ogg", ".wav"):
            p = os.path.join(self._amb_dir, stem + ext)
            if os.path.exists(p):
                return p
        return None

    # -------------------------
    # cooldowns
    # -------------------------
    def set_cooldown(self, key: str, seconds: float):
        self._cooldowns[str(key)] = max(0.0, float(seconds))

    def _can_play(self, key: str) -> bool:
        if not self.enabled:
            return False
        k = str(key)
        cd = float(self._cooldowns.get(k, 0.0))
        if cd <= 0.0:
            return True
        now = pygame.time.get_ticks() / 1000.0
        last = float(self._last_play_time.get(k, -1e9))
        return (now - last) >= cd

    def _mark_played(self, key: str):
        self._last_play_time[str(key)] = pygame.time.get_ticks() / 1000.0

    # -------------------------
    # defaults
    # -------------------------
    def load_defaults(self):
        # UI
        self.ui["move"] = self._load_variants("ui_move")
        self.ui["select"] = self._load_variants("ui_select")
        self.ui["back"] = self._load_variants("ui_back")

        # Abilities / gameplay
        self.sfx["q"] = self._load_variants("q_shot")
        self.sfx["r"] = self._load_variants("r_shot")
        self.sfx["e"] = self._load_variants("e_blast")
        self.sfx["f"] = self._load_variants("f_shell")
        self.sfx["melee"] = self._load_variants("melee")

        # State / world
        self.sfx["game_over"] = self._load_variants("game_over")
        self.sfx["pause"] = self._load_variants("pause")
        self.sfx["resume"] = self._load_variants("resume")
        self.sfx["hurt"] = self._load_variants("player_hurt")
        self.sfx["room_clear"] = self._load_variants("room_clear")
        self.sfx["door_open"] = self._load_variants("door_open")
        self.sfx["door_travel"] = self._load_variants("door_travel")
        self.sfx["portal"] = self._load_variants("portal_spawn")

        # Combat feedback
        self.sfx["enemy_hit"] = self._load_variants("enemy_hit")
        self.sfx["enemy_die"] = self._load_variants("enemy_die")
        self.sfx["crate_break"] = self._load_variants("crate_break")
        self.sfx["rock_break"] = self._load_variants("rock_break")

        # Cooldowns
        self.set_cooldown("hurt", 0.12)
        self.set_cooldown("door_travel", 0.20)
        self.set_cooldown("door_open", 0.25)
        self.set_cooldown("room_clear", 0.25)
        self.set_cooldown("portal", 0.50)

        self.set_cooldown("enemy_hit", 0.03)
        self.set_cooldown("enemy_die", 0.06)
        self.set_cooldown("crate_break", 0.10)
        self.set_cooldown("rock_break", 0.10)

        # Ambience (paths)
        self.ambience["normal"] = self._find_ambience_file("normal")
        self.ambience["boss"] = self._find_ambience_file("boss")
        self.ambience["secret"] = self._find_ambience_file("secret")
        self.ambience["shop"] = self._find_ambience_file("shop")
        self.ambience["treasure"] = self._find_ambience_file("treasure")

        # Music (paths)
        self.music_tracks["menu"] = self._find_music_file("menu")
        self.music_tracks["game"] = self._find_music_file("game")
        self.music_tracks["boss"] = self._find_music_file("boss")

        self.apply_volumes()

    # -------------------------
    # volumes
    # -------------------------
    def apply_volumes(self):
        if not self.enabled:
            return

        self._mv = max(0.0, min(1.0, float(self.master_volume)))
        self._sv = max(0.0, min(1.0, float(self.sfx_volume)))
        self._musv = max(0.0, min(1.0, float(self.music_volume)))

        # music is global mixer music channel
        try:
            pygame.mixer.music.set_volume(self._mv * self._musv if self.music_enabled else 0.0)
        except Exception:
            pass

        # fixed channels
        try:
            base = self._mv * self._sv
            pygame.mixer.Channel(self.CH_UI).set_volume(base)
            pygame.mixer.Channel(self.CH_PLAYER).set_volume(base)
            pygame.mixer.Channel(self.CH_WORLD).set_volume(base)
            pygame.mixer.Channel(self.CH_AMBIENCE).set_volume(base * 0.65)
        except Exception:
            pass

    # -------------------------
    # play helpers
    # -------------------------
    def _pick_sound(self, bank, key: str):
        entry = bank.get(key)
        if entry is None:
            return None
        if isinstance(entry, list):
            return random.choice(entry) if entry else None
        return entry

    def play_ui(self, key: str):
        tag = f"ui:{key}"
        if not self._can_play(tag):
            return
        snd = self._pick_sound(self.ui, key)
        if snd is None:
            return
        try:
            pygame.mixer.Channel(self.CH_UI).play(snd)
            self._mark_played(tag)
        except Exception:
            pass

    def play_sfx(self, key: str, channel: int):
        if not self._can_play(key):
            return
        snd = self._pick_sound(self.sfx, key)
        if snd is None:
            return
        try:
            pygame.mixer.Channel(int(channel)).play(snd)
            self._mark_played(key)
        except Exception:
            pass

    def _pan_from_x(self, x: float, bounds: pygame.Rect) -> tuple[float, float]:
        if bounds.width <= 1:
            return 1.0, 1.0
        t = (float(x) - float(bounds.left)) / float(bounds.width)
        t = max(0.0, min(1.0, t))
        left = (1.0 - t) ** 0.5
        right = (t) ** 0.5
        return left, right

    def play_sfx_world_at(self, key: str, x: float, bounds: pygame.Rect):
        """
        Plays SFX on any free channel with stereo panning.
        Note: uses find_channel(True) to force allocation.
        """
        if not self.enabled:
            return
        if not self._can_play(key):
            return

        snd = self._pick_sound(self.sfx, key)
        if snd is None:
            return

        ch = pygame.mixer.find_channel(True)
        if ch is None:
            return

        lpan, rpan = self._pan_from_x(x, bounds)
        base = self._mv * self._sv
        try:
            ch.set_volume(base * lpan, base * rpan)
            ch.play(snd)
            self._mark_played(key)
        except Exception:
            pass

    # -------------------------
    # music / ambience
    # -------------------------
    def play_music(self, key: str, loop: bool = True, fade_ms: int = 250):
        """
        Fix: pygame.mixer.music.play signature is (loops=0, start=0.0, fade_ms=0).
        Old bug: passing fade_ms as 2nd positional arg => start=fade_ms seconds (silence).
        """
        if not self.enabled:
            return
        if not self.music_enabled:
            self.stop_music(fade_ms=fade_ms)
            return

        path = self.music_tracks.get(key)
        if not path:
            return
        if self._current_music_key == key:
            return

        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(int(fade_ms))
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1 if loop else 0, start=0.0, fade_ms=int(fade_ms))
            self._current_music_key = key
            self.apply_volumes()
        except Exception:
            pass

    def stop_music(self, fade_ms: int = 250):
        if not self.enabled:
            return
        try:
            if fade_ms and pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(int(fade_ms))
            else:
                pygame.mixer.music.stop()
            self._current_music_key = None
        except Exception:
            pass

    def set_ambience(self, key: str | None):
        if not self.enabled:
            return
        if key == self._current_ambience_key:
            return

        amb_ch = pygame.mixer.Channel(self.CH_AMBIENCE)
        try:
            amb_ch.stop()
        except Exception:
            pass

        self._current_ambience_key = key
        if key is None:
            return

        path = self.ambience.get(key)
        if not path:
            return

        snd = self._try_load_sound(path)
        if snd is None:
            return

        try:
            amb_ch.play(snd, loops=-1)
        except Exception:
            pass


AUDIO = AudioManager()


def apply_audio_from_app(app_config):
    """
    app_config: object with fields master_volume, sfx_volume, music_volume, music_enabled
    """
    AUDIO.master_volume = float(app_config.master_volume)
    AUDIO.sfx_volume = float(app_config.sfx_volume)
    AUDIO.music_volume = float(app_config.music_volume)
    AUDIO.music_enabled = bool(app_config.music_enabled)
    AUDIO.apply_volumes()