from client.scenes.base import BaseScene, Scenes
from client.scenes.game import GameScene
from client.scenes.initial_scene import InitialScene
from client.scenes.login import LoginScene
from client.scenes.main_menu import MainMenu
from client.scenes.matchmaking import MatchmakingScene
from client.scenes.start import StartScene

SCENES_MAP: dict[Scenes, type[BaseScene]] = {
    Scenes.START: StartScene,
    Scenes.LOGIN: LoginScene,
    Scenes.MATCHMAKING: MatchmakingScene,
    Scenes.GAME: GameScene,
    Scenes.MAIN_MENU: MainMenu,
    Scenes.INITIAL_SCENE: InitialScene,
}
"""Mapping of scenes to their respective classes."""


__all__ = ["SCENES_MAP", "Scenes"]
