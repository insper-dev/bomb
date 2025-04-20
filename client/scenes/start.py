import pygame

from client.components import BaseComponent, TextArea
from client.scenes.base import BaseScene, Scenes


class StartScene(BaseScene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.time = {"time_elapsed": 0, "initial_time": -1, "time_counter": 1}
        self.text: BaseComponent = [
            TextArea(
                self.app.screen, self.app.screen_center, "Pygame Community", text_type="title"
            ),
            TextArea(self.app.screen, self.app.screen_center, "Moriaty", text_type="title"),
            TextArea(
                self.app.screen, self.app.screen_center, "Margenta Production", text_type="title"
            ),
        ]
        self.transition_time = 500  # Miliseconds
        self.text_index = 0
        self.add_component(self.text[self.text_index])

    def render(self) -> None:
        # Calculate the time
        t1 = pygame.time.get_ticks()
        self.time["time_elapsed"] = t1 - self.time["initial_time"]
        self.time["initial_time"] = t1
        self.time["time_counter"] += self.time["time_elapsed"]

        if self.time["time_counter"] > self.transition_time:
            self.remove_component(self.text[self.text_index])
            self.text_index += 1
            if self.text_index < len(self.text):
                self.add_component(self.text[self.text_index])
                self.time["time_counter"] = 0
            else:
                self.app.current_scene = Scenes.INITIAL_SCENE

    def handle_event(self, event) -> None:
        return
