import pygame

from client.components import BaseComponent, Text
from client.scenes.base import BaseScene, Scenes


class StartScene(BaseScene):
    TRANSITION_TIME = 750

    def __init__(self, app) -> None:
        super().__init__(app)
        self._initialize_timer()
        self._initialize_texts()
        self.text_index = 0
        self.add_component(self.texts[self.text_index])

    def _initialize_timer(self) -> None:
        self.time = {"time_elapsed": 0, "initial_time": pygame.time.get_ticks(), "time_counter": 0}

    def _initialize_texts(self) -> None:
        self.texts: list[BaseComponent] = [
            Text(self.app.screen, self.app.screen_center, "Pygame Community", text_type="title"),
            Text(self.app.screen, self.app.screen_center, "Moriaty", text_type="title"),
            Text(self.app.screen, self.app.screen_center, "Margenta Production", text_type="title"),
        ]

    def render(self) -> None:
        self._update_timer()
        self._handle_transition()

    def _update_timer(self) -> None:
        current_time = pygame.time.get_ticks()
        self.time["time_elapsed"] = current_time - self.time["initial_time"]
        self.time["initial_time"] = current_time
        self.time["time_counter"] += self.time["time_elapsed"]

    def _handle_transition(self) -> None:
        if self.time["time_counter"] > self.TRANSITION_TIME:
            self.remove_component(self.texts[self.text_index])
            self.text_index += 1

            if self.text_index < len(self.texts):
                self.add_component(self.texts[self.text_index])
                self.time["time_counter"] = 0
            else:
                self.app.current_scene = Scenes.INITIAL_SCENE

    def handle_event(self, event) -> None:
        pass
