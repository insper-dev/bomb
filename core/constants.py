from pathlib import Path
from typing import Literal

import pygame

from core.types import Cordinates, Thickness, comp, is_disabled, is_focused

pygame.init()

ROOT = Path(__file__).parent.parent


SESSION_FILE = ROOT / ".session.json"

# Constants for the game

# Color constants
PURPLE = (1, 5, 68)
ROSE = (243, 45, 107)
WHITE = (255, 255, 255)
WHITE_GRAY = (200, 200, 200)
SOUTH_GRAY = (180, 180, 180)
GRAY = (128, 128, 128)
BLACK = (0, 0, 0)
YELLOW = (243, 255, 107)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)


# Constants for the components

SIZE_MAP: dict[
    is_focused : dict[comp : dict[Literal["sm", "md", "lg"] : tuple[Cordinates, Thickness]]]
] = {
    False: {
        "button": {
            "sm": ((100, 30), 2),
            "md": ((150, 40), 3),
            "lg": ((200, 50), 4),
        },
        "text_area": {
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
    True: {
        "button": {
            "sm": ((110, 35), 3),
            "md": ((160, 45), 4),
            "lg": ((210, 55), 5),
        },
        "text area": {
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


VARIANT_MAP: dict[
    is_disabled : dict[
        is_focused : dict[
            Literal["standard", "primary", "secondary", "outline"], dict[str, pygame.color.Color]
        ]
    ]
] = {
    False: {
        False: {
            "standard": {"bg": PURPLE, "text": ROSE, "border": WHITE},
            "primary": {"bg": BLUE, "text": WHITE, "border": BLACK},
            "secondary": {"bg": GREEN, "text": WHITE, "border": BLACK},
            "outline": {"bg": WHITE, "text": BLACK, "border": BLACK},
        },
        True: {
            "standard": {"bg": PURPLE, "text": YELLOW, "border": WHITE},
            "primary": {"bg": BLUE, "text": GRAY, "border": GRAY},
            "secondary": {"bg": GREEN, "text": GRAY, "border": GRAY},
            "outline": {"bg": WHITE, "text": GRAY, "border": GRAY},
        },
    },
    True: {
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

FONT_STYLES: dict[
    Literal["normal", "bold", "italic", "bold_italic"],
    tuple[str, int],
] = {
    None: None,
    "normal": "freesansbold.ttf",
    "bold": "freesansbold.ttf",
    "italic": "freesansbold.ttf",
    "bold_italic": "freesansbold.ttf",
}

FONT_SIZE_MAP: dict[
    is_focused : dict[
        Literal["standard", "title", "subtitle", "text"] : dict[Literal["sm", "md", "lg"], int]
    ]
] = {
    False: {
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
    True: {
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
