from client.scenes.base import BaseScene, Scenes
from client.scenes.game import GameScene
from client.scenes.game_over import GameOverScene
from client.scenes.login import LoginScene
from client.scenes.matchmaking import MatchmakingScene
from client.scenes.start import StartScene

SCENES_MAP: dict[Scenes, type[BaseScene]] = {
    Scenes.START: StartScene,
    Scenes.LOGIN: LoginScene,
    Scenes.MATCHMAKING: MatchmakingScene,
    Scenes.GAME: GameScene,
    Scenes.GAME_OVER: GameOverScene,
}
"""Mapping of scenes to their respective classes."""


__all__ = ["SCENES_MAP", "Scenes"]
