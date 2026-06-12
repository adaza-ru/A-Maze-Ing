import os
from typing import Optional
from just_playback import Playback

class AudioManager:
    def __init__(self):
        self._player = Playback()
        self._current_track: Optional[str] = None
        self._audio_dir = os.path.join(os.path.dirname(__file__), "audio")

    def update_audio_state(self, display_mode: str, rainbow_mode: bool):
        target_track = None

        if display_mode == "cursed":
            target_track = "RickRoll"
        elif rainbow_mode:
            target_track = "TheRaverOne"

        if target_track != self._current_track:
            self.stop()
            if target_track:
                self._play(target_track)

    def _play(self, track_name: str):
        file_path = os.path.join(self._audio_dir, f"{track_name}.mp3")
        
        if os.path.exists(file_path):
            try:
                self._player.load_file(file_path)
                self._player.play()
                self._player.loop_at_end(True) # Loop infinito
                self._current_track = track_name
            except Exception:
                # Falla silenciosamente (como en tu WSL actual) para no 
                # romper el juego si hay problemas de drivers de audio
                self._current_track = None

    def stop(self):
        if self._player.active:
            self._player.stop()
        self._current_track = None