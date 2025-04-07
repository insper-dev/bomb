import pygame

from client.scenes.base import BaseScene


class StartScene(BaseScene):
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.app.running = False

    def render(self) -> None:
        font = pygame.font.SysFont(None, 80)
        self.app.screen.fill((0, 0, 0))
        # TODO: define color constants at core.constants
        text = font.render("Welcome", True, (255, 255, 255))
        text_rect = text.get_rect(center=self.app.screen_center)

        self.app.screen.blit(text, text_rect)
