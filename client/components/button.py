import pygame

from client.components import BaseComponent


class Button(BaseComponent):
    def _init_surface(self) -> pygame.Surface:
        """
        Initialize the surface of the button.
        """
        cordinate, thickness = self._get_size()
        middle = (cordinate[0] // 2, cordinate[1] // 2)
        radius = 10

        # Create main surface and rect
        surface = self._create_surface(cordinate)
        rect = surface.get_rect()

        # Create the text surface
        font = self._get_font()
        text_surface = font.render(self.label, True, self._get_color("text"))

        # draw background
        background_rect = pygame.Rect(0, 0, cordinate[0], cordinate[1])
        background_rect.center = middle
        pygame.draw.rect(surface, self._get_color("bg"), background_rect, border_radius=radius)

        # draw the border
        pygame.draw.rect(
            surface, self._get_color("border"), rect, border_radius=radius, width=thickness
        )

        # blit the text surface
        surface.blit(text_surface, text_surface.get_rect(center=middle))

        return surface
