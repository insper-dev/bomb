import pygame

from client.components import BaseComponent


class State(BaseComponent):
    def __init__(
        self,
        window,
        position,
        label,
        variant="standard",
        size="md",
        text_type="standard",
        hover=True,
        is_topleft=False,
        *,
        callback=...,
    ) -> None:
        super().__init__(
            window, position, label, variant, size, text_type, hover, is_topleft, callback=callback
        )
        self.value: str = ""
        self.ini_label = self.label
        self.active: bool = False
        self.time = {"elapsed_time": 0, "last_tick": pygame.time.get_ticks(), "time_counter": 0}
        self.sprites = ["", ".", "..", "..."]
        self.add = ""
        self.holder = "Loading"

    def _init_surface(self) -> pygame.Surface:
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

    def _render(self) -> None:
        if self.active:
            t1 = pygame.time.get_ticks()
            self.time["elapsed_time"] += t1 - self.time["last_tick"]
            self.time["last_tick"] = t1

            if self.time["elapsed_time"] > 500:
                self.time["elapsed_time"] = 0
                index = self.sprites.index(self.value)
                index += 1
                if index >= len(self.sprites):
                    index = 0
                self.value = self.sprites[index]
            self.label = self.holder + self.value
        else:
            self.label = self.ini_label

    def _callback(self) -> None:
        self.active = not self.active
        if self.active:
            self.callback()
