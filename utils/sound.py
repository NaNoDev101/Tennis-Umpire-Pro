"""
utils/sound.py — Sound notification manager for Tennis Umpire Pro.

Uses ``canberra-gtk-play`` (Linux desktop notification sounds).
Failures are logged rather than silently swallowed so that developers
can diagnose missing binaries or incorrect event names.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


# Map of logical sound names → canberra event IDs
_SOUND_MAP: dict[str, str] = {
    "point": "audio-volume-change",
    "game":  "complete",
    "set":   "dialog-information",
    "match": "dialog-information",
}


class SoundManager:
    """Play desktop notification sounds via ``canberra-gtk-play``.

    Args:
        enabled: Whether sound is active at initialisation.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled: bool = enabled

    def play(self, sound_type: str) -> None:
        """Play the sound associated with *sound_type*.

        Args:
            sound_type: One of ``"point"``, ``"game"``, ``"set"``,
                        ``"match"``.  Unknown keys are logged as warnings
                        and silently skipped.
        """
        if not self.enabled:
            return

        event_id = _SOUND_MAP.get(sound_type)
        if not event_id:
            logger.warning("SoundManager: unknown sound type %r", sound_type)
            return

        try:
            subprocess.Popen(
                ["canberra-gtk-play", "-i", event_id],
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            logger.debug("canberra-gtk-play not found — sound skipped.")
        except Exception:
            logger.exception("SoundManager: unexpected error playing %r", sound_type)
