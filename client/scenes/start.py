import pygame

from client.scenes.base import BaseScene


class StartScene(BaseScene):
    def update(self) -> None:
        font = pygame.font.SysFont(None, 80)
        self.app.screen.fill((0, 0, 0))
        # TODO: define color constants at core.constants
        text = font.render("Welcome", True, (255, 255, 255))
        text_rect = text.get_rect(center=self.app.screen_center)
        self.app.screen.blit(text, text_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.app.running = False
