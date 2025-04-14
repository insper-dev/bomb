from client.scenes.base import BaseScene, Scenes
from client.scenes.start import StartScene

SCENES_MAP: dict[Scenes, type[BaseScene]] = {
    Scenes.START: StartScene,
    # Scenes.LOGIN: LoginScene,
    # Scenes.MATCHMAKING: MatchmakingScene,
    # Scenes.GAME: GameScene,
}
"""Mapping of scenes to their respective classes."""


__all__ = ["SCENES_MAP", "Scenes"]
