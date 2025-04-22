from pathlib import Path

import pygame

from core.types import (
    ComponentSize,
    ComponentType,
    ComponentVariant,
    Coordinate,
    FontSize,
    FontStyle,
    IsDisabled,
    IsFocused,
    ParticleType,
    PlayerDirectionState,
    Thickness,
)

pygame.init()

ROOT = Path(__file__).parent.parent

ASSETS_PATH = ROOT / "client" / "assets"
IMAGES_PATH = ASSETS_PATH / "images"

SESSION_FILE = ROOT / ".session.json"

# Constants for the game

# Color constants
PURPLE = pygame.Color(1, 5, 68)
ROSE = pygame.Color(243, 45, 107)
WHITE = pygame.Color(255, 255, 255)
WHITE_GRAY = pygame.Color(200, 200, 200)
SOUTH_GRAY = pygame.Color(180, 180, 180)
GRAY = pygame.Color(128, 128, 128)
BLACK = pygame.Color(0, 0, 0)
YELLOW = pygame.Color(243, 255, 107)
BLUE = pygame.Color(0, 0, 255)
GREEN = pygame.Color(0, 255, 0)


# Constants for the components
FOCUSED = ENABLED = True
NOT_FOCUSED = DISABLED = False

SIZE_MAP: dict[
    IsFocused, dict[ComponentType, dict[ComponentSize, tuple[Coordinate, Thickness]]]
] = {
    NOT_FOCUSED: {
        "button": {
            "sm": ((100, 30), 2),
            "md": ((150, 40), 3),
            "lg": ((200, 50), 4),
        },
        "text": {
            "sm": ((100, 30), 2),
            "md": ((150, 40), 3),
            "lg": ((200, 50), 4),
        },
        "input": {
            "sm": ((200, 30), 2),
            "md": ((280, 40), 3),
            "lg": ((360, 50), 4),
        },
        "state": {
            "sm": ((120, 30), 2),
            "md": ((170, 40), 3),
            "lg": ((220, 50), 4),
        },
    },
    FOCUSED: {
        "button": {
            "sm": ((110, 35), 3),
            "md": ((160, 45), 4),
            "lg": ((210, 55), 5),
        },
        "text": {
            "sm": ((110, 35), 3),
            "md": ((160, 45), 4),
            "lg": ((210, 55), 5),
        },
        "input": {
            "sm": ((220, 35), 3),
            "md": ((300, 45), 4),
            "lg": ((380, 55), 5),
        },
        "state": {
            "sm": ((125, 35), 3),
            "md": ((175, 45), 4),
            "lg": ((225, 55), 5),
        },
    },
}


VARIANT_MAP: dict[IsDisabled, dict[IsFocused, dict[ComponentVariant, dict[str, pygame.Color]]]] = {
    DISABLED: {
        NOT_FOCUSED: {
            "standard": {"bg": PURPLE, "text": ROSE, "border": WHITE},
            "primary": {"bg": BLUE, "text": WHITE, "border": BLACK},
            "secondary": {"bg": GREEN, "text": WHITE, "border": BLACK},
            "outline": {"bg": WHITE, "text": BLACK, "border": BLACK},
        },
        FOCUSED: {
            "standard": {"bg": PURPLE, "text": YELLOW, "border": WHITE},
            "primary": {"bg": BLUE, "text": GRAY, "border": GRAY},
            "secondary": {"bg": GREEN, "text": GRAY, "border": GRAY},
            "outline": {"bg": WHITE, "text": GRAY, "border": GRAY},
        },
    },
    ENABLED: {
        False: {
            "standard": {"bg": WHITE, "text": BLACK, "border": BLACK},
            "primary": {"bg": BLUE, "text": WHITE, "border": BLACK},
            "secondary": {"bg": GREEN, "text": WHITE, "border": BLACK},
            "outline": {"bg": SOUTH_GRAY, "text": GRAY, "border": BLACK},
        },
        True: {
            "standard": {"bg": WHITE, "text": GRAY, "border": GRAY},
            "primary": {"bg": BLUE, "text": GRAY, "border": GRAY},
            "secondary": {"bg": GREEN, "text": GRAY, "border": GRAY},
            "outline": {"bg": SOUTH_GRAY, "text": GRAY, "border": GRAY},
        },
    },
}

FONT_MAP: dict[FontStyle, str] = {
    "normal": "freesansbold.ttf",
    "bold": "freesansbold.ttf",
    "italic": "freesansbold.ttf",
    "bold_italic": "freesansbold.ttf",
}

FONT_SIZE_MAP: dict[IsFocused, dict[FontSize, dict[ComponentSize, int]]] = {
    NOT_FOCUSED: {
        "standard": {
            "sm": 20,
            "md": 24,
            "lg": 30,
        },
        "title": {
            "sm": 48,
            "md": 60,
            "lg": 72,
        },
        "subtitle": {
            "sm": 36,
            "md": 42,
            "lg": 48,
        },
        "text": {
            "sm": 16,
            "md": 20,
            "lg": 24,
        },
    },
    FOCUSED: {
        "standard": {
            "sm": 22,
            "md": 26,
            "lg": 32,
        },
        "title": {
            "sm": 50,
            "md": 62,
            "lg": 74,
        },
        "subtitle": {
            "sm": 20,
            "md": 26,
            "lg": 32,
        },
        "text": {
            "sm": 18,
            "md": 22,
            "lg": 26,
        },
    },
}

# Game constants
GAME_ALPHABET_KEYS = [pygame.key.key_code(key) for key in "abcdefghijklmnopqrstuvwxyz"]

MODULE_SIZE = 64

# Blocks and Floors
BLOCKS_PATH = IMAGES_PATH / "blocks"

BLCOKS: dict[str, pygame.Surface] = {
    "areia": pygame.transform.scale(
        pygame.image.load(BLOCKS_PATH / "Areia.png"), (MODULE_SIZE, MODULE_SIZE)
    ),
    "caixa": pygame.transform.scale(
        pygame.image.load(BLOCKS_PATH / "Caixa.png"), (MODULE_SIZE, MODULE_SIZE)
    ),
    "diamante": pygame.transform.scale(
        pygame.image.load(BLOCKS_PATH / "Diamante.png"), (MODULE_SIZE, MODULE_SIZE)
    ),
    "metal": pygame.transform.scale(
        pygame.image.load(BLOCKS_PATH / "Metal.png"), (MODULE_SIZE, MODULE_SIZE)
    ),
}

FLOORS: dict[str, pygame.Color] = {
    "f_shed1": pygame.Color(23, 23, 23),
    "f_sehd2": pygame.Color(5, 5, 5),
}

# Bomb
BOMB_PATH = IMAGES_PATH / "bomb"
BOMB_COKING: list[pygame.Surface] = [
    pygame.transform.scale(
        pygame.image.load(BOMB_PATH / "bomb_state_1.png"),
        (MODULE_SIZE, MODULE_SIZE),
    ),
    pygame.transform.scale(
        pygame.image.load(BOMB_PATH / "bomb_state_2.png"),
        (MODULE_SIZE, MODULE_SIZE),
    ),
    pygame.transform.scale(
        pygame.image.load(BOMB_PATH / "bomb_state_3.png"),
        (MODULE_SIZE, MODULE_SIZE),
    ),
    pygame.transform.scale(
        pygame.image.load(BOMB_PATH / "bomb_state_4.png"),
        (MODULE_SIZE, MODULE_SIZE),
    ),
    pygame.transform.scale(
        pygame.image.load(BOMB_PATH / "bomb_state_5.png"),
        (MODULE_SIZE, MODULE_SIZE),
    ),
]

# Particles

PARTICLES_PATH = IMAGES_PATH / "particles"
EXPLOSION_PARTICLES: dict[ParticleType, list[pygame.Surface]] = {
    "geo": [
        pygame.transform.scale(
            pygame.image.load(PARTICLES_PATH / "particles_geo.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        )
    ],
    "tip": [
        pygame.transform.rotate(
            pygame.transform.scale(
                pygame.image.load(PARTICLES_PATH / "particles_tip.jpeg"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            angle,
        )
        for angle in range(0, 271, 90)
    ],
    "tail": [
        pygame.transform.rotate(
            pygame.transform.scale(
                pygame.image.load(PARTICLES_PATH / "particles_tail.jpeg"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            angle,
        )
        for angle in range(0, 271, 90)
    ],
}

# Players
# TODO: explícito é melhor que implícito.
CARLITOS_PATH = IMAGES_PATH / "carlitos_player"
CARLITOS: dict[PlayerDirectionState, list[pygame.Surface]] = {
    "right": [
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "horizontal_1.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "horizontal_2.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "horizontal_3.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
    "left": [
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(CARLITOS_PATH / "horizontal_1.jpeg"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(CARLITOS_PATH / "horizontal_2.jpeg"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(CARLITOS_PATH / "horizontal_3.jpeg"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
    ],
    "down": [
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "front_1.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "front_2.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "front_3.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
    "up": [
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "back_1.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "back_2.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "back_3.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
    "stand_by": [
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "horizontal_2.jpeg"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
}
