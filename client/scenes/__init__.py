from client.scenes.base import BaseScene, Scenes
from client.scenes.config import ConfigScene
from client.scenes.game import GameScene
from client.scenes.game_over import GameOverScene
from client.scenes.initial_scene import InitialScene
from client.scenes.login import LoginScene
from client.scenes.main_menu import MainMenuScene
from client.scenes.matchmaking import MatchmakingScene
from client.scenes.start import StartScene

SCENES_MAP: dict[Scenes, type[BaseScene]] = {
    Scenes.START: StartScene,
    Scenes.LOGIN: LoginScene,
    Scenes.MATCHMAKING: MatchmakingScene,
    Scenes.GAME: GameScene,
    Scenes.MAIN_MENU: MainMenuScene,
    Scenes.INITIAL_SCENE: InitialScene,
    Scenes.GAME_OVER: GameOverScene,
    Scenes.CONFIG: ConfigScene,
}
"""Mapping of scenes to their respective classes."""


__all__ = ["SCENES_MAP", "Scenes"]
