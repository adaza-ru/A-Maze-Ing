"""
audio_manager.py - Background audio playback via just_playback.

Plays a looping track based on the current display/rainbow mode:
  - DISPLAY_MODE == "cursed" -> RickRoll   (priority)
  - RAINBOW_MODE == True     -> TheRaverOne
  - Otherwise                -> silence

just_playback/miniaudio write ALSA/JACK diagnostics directly to the
process's stderr file descriptor, bypassing Python exceptions entirely.
All calls into the library are wrapped with _suppress_stderr() to avoid
corrupting blessed's alternate screen buffer.

If no playback device is available at all, the manager degrades to a
silent no-op rather than crashing the whole engine.
"""

import contextlib
import os
from typing import Iterator, Optional

from just_playback import Playback


@contextlib.contextmanager
def _suppress_stderr() -> Iterator[None]:
    """
    Temporarily redirect fd 2 (stderr) to /dev/null.

    just_playback/miniaudio write low-level ALSA/JACK diagnostics
    directly to the C-level stderr fd. Without this, that output can
    corrupt blessed's alternate screen buffer.
    """
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved = os.dup(2)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(devnull)
        os.close(saved)


class AudioManager:
    """
    Manages background music playback for rainbow/cursed modes.

    Tracks the currently playing track and only restarts playback when
    the target track changes, avoiding unnecessary reloads every frame.
    Tracks that fail to load or play are blacklisted so they are not
    retried every frame.

    If no playback device is available, the manager silently becomes
    a no-op so the engine never crashes because of audio.
    """

    def __init__(self) -> None:
        self._current_track: Optional[str] = None
        self._failed_tracks: set[str] = set()
        self._audio_dir = os.path.join(os.path.dirname(__file__), "audio")
        self._player: Optional[Playback] = None

        try:
            with _suppress_stderr():
                self._player = Playback()
        except Exception:
            self._player = None

    def update_audio_state(
        self,
        display_mode: str,
        rainbow_mode: bool,
    ) -> None:
        """
        Sync playback with the current display/rainbow mode.

        Args:
            display_mode: Current MazeConfig.display_mode (lowercase).
            rainbow_mode: Current MazeConfig.rainbow_mode.
        """
        if self._player is None:
            return

        target_track: Optional[str] = None
        if display_mode == "cursed":
            target_track = "RickRoll"
        elif rainbow_mode:
            target_track = "TheRaverOne"

        if target_track in self._failed_tracks:
            target_track = None

        if target_track != self._current_track:
            self.stop()
            if target_track:
                self._play(target_track)

    def stop(self) -> None:
        """Stop any currently playing track."""
        if self._player is None:
            return

        if self._player.active:
            with _suppress_stderr():
                self._player.stop()
        self._current_track = None

    def _play(self, track_name: str) -> None:
        """Load and start looping playback of *track_name*."""
        if self._player is None:
            return

        file_path = os.path.join(self._audio_dir, f"{track_name}.mp3")
        if not os.path.exists(file_path):
            self._failed_tracks.add(track_name)
            return

        try:
            with _suppress_stderr():
                self._player.load_file(file_path)
                self._player.play()
                self._player.loop_at_end(True)
            self._current_track = track_name
        except Exception:
            self._failed_tracks.add(track_name)
            self._current_track = None
