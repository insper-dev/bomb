import pygame

from client.components import BaseComponent


class TextArea(BaseComponent):
    def _init_surface(self) -> pygame.Surface:
        """
        Initialize the surface of the TextArea.
        """
        # Create the text surface
        font = self._get_font()
        text_surface = font.render(self.label, True, self._get_color("text"))

        return text_surface
