import pygame

from client.components import BaseComponent


class Input(BaseComponent):
    def __init__(
        self,
        window,
        label,
        position,
        variant="standard",
        size="md",
        text_type="standard",
        hover=True,
        is_topleft=False,
        *,
        callback=lambda: None,
    ) -> None:
        super().__init__(
            window, position, label, variant, size, text_type, hover, is_topleft, callback=callback
        )
        self.value: str = ""
        self.ini_label = "" if r"\h" == self.label[-2:] else self.label[:-2]
        self.secretive = self.label[:-2].lower() == "password"
        self.active: bool = False
        self.time = {"elapsed_time": 0, "last_tick": pygame.time.get_ticks(), "time_counter": 0}
        self.animation_particle = "|"
        self.add = ""

    def _init_surface(self) -> pygame.Surface:
        """
        Initialize the surface of the input.
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

    def _render(self) -> None:
        t1 = pygame.time.get_ticks()
        self.time["elapsed_time"] = t1 - self.time["last_tick"]
        self.time["last_tick"] = t1
        self.time["time_counter"] += self.time["elapsed_time"]
        if self.active:
            self.is_focused = True
            self.label = self.value + self.add
            if self.secretive:
                self.label = len(self.value) * "#" + self.add
            if self.time["time_counter"] > 500:
                if self.add != self.animation_particle:
                    self.add = self.animation_particle
                    self.time["time_counter"] = 0
                else:
                    self.add = " "
                    self.time["time_counter"] = 0
        else:
            self.label = self.value

        if self.label == "" and not self.active:
            self.label = self.ini_label
        elif self.secretive and not self.active:
            if self.secretive:
                self.label = len(self.value) * "*"

    def _callback(self) -> None:
        self.active = not self.active
        self.label = self.value
        if self.label == "" and not self.active:
            self.label = self.ini_label

    def _handle_event(self, event) -> None:
        if self.active:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if not self.rect.collidepoint(event.pos):
                    self._callback()
            if event.type == pygame.KEYDOWN:
                if event.unicode.isprintable():
                    self.value += event.unicode
                elif event.key == pygame.K_BACKSPACE:
                    self.value = self.value[0 : len(self.value) - 1]
                elif event.key == pygame.K_SPACE:
                    self.value += " "
                elif event.key == pygame.K_RETURN:
                    self.callback()
