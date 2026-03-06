# config/app_config.py
import json
import os


class AppConfig:
    FILE_NAME = "settings.json"

    def __init__(self):
        self.fullscreen = False
        self._video_dirty = False

        self.difficulty_scale = 1.0

        self.master_volume = 0.8
        self.sfx_volume = 0.8
        self.music_volume = 0.6
        self.music_enabled = True
        self._audio_dirty = False

    def _project_dir(self) -> str:
        # config/ -> project root
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _path(self) -> str:
        return os.path.join(self._project_dir(), self.FILE_NAME)

    def load(self):
        p = self._path()
        if not os.path.exists(p):
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self.fullscreen = bool(data.get("fullscreen", self.fullscreen))
        self.difficulty_scale = float(data.get("difficulty_scale", self.difficulty_scale))
        self.master_volume = float(data.get("master_volume", self.master_volume))
        self.sfx_volume = float(data.get("sfx_volume", self.sfx_volume))
        self.music_volume = float(data.get("music_volume", self.music_volume))
        self.music_enabled = bool(data.get("music_enabled", self.music_enabled))

        self.difficulty_scale = max(1.0, min(2.0, self.difficulty_scale))
        self.master_volume = max(0.0, min(1.0, self.master_volume))
        self.sfx_volume = max(0.0, min(1.0, self.sfx_volume))
        self.music_volume = max(0.0, min(1.0, self.music_volume))

        self._video_dirty = True
        self._audio_dirty = True

    def save(self):
        p = self._path()
        data = {
            "fullscreen": bool(self.fullscreen),
            "difficulty_scale": float(self.difficulty_scale),
            "master_volume": float(self.master_volume),
            "sfx_volume": float(self.sfx_volume),
            "music_volume": float(self.music_volume),
            "music_enabled": bool(self.music_enabled),
        }
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._video_dirty = True

    def consume_video_dirty(self) -> bool:
        d = self._video_dirty
        self._video_dirty = False
        return d

    def consume_audio_dirty(self) -> bool:
        d = self._audio_dirty
        self._audio_dirty = False
        return d

    def mark_audio_dirty(self):
        self._audio_dirty = True


APP = AppConfig()
