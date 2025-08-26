from pathlib import Path

import pygame

from core.models.game import GameTheme, MapBlockType
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
    PlayerType,
    Thickness,
)

ROOT = Path(__file__).parent.parent

CLIENT_TITLE = "Bomberman"
CLIENT_WIDTH = 1200
CLIENT_HEIGHT = 800
CLIENT_FPS = 60

ASSETS_PATH = ROOT / "client" / "assets"
IMAGES_PATH = ASSETS_PATH / "images"

SESSION_FILE = ROOT / ".session.json"

# Constants for the game

# Modern Color Palette - Identidade Visual Melhorada
DARK_NAVY = pygame.Color(15, 23, 42)  # Background principal
SLATE_GRAY = pygame.Color(51, 65, 85)  # Elementos secundários
ACCENT_BLUE = pygame.Color(59, 130, 246)  # Destaque principal
ACCENT_GREEN = pygame.Color(34, 197, 94)  # Sucesso/confirmação
ACCENT_RED = pygame.Color(239, 68, 68)  # Erro/perigo
ACCENT_YELLOW = pygame.Color(251, 191, 36)  # Aviso/atenção
ACCENT_PURPLE = pygame.Color(147, 51, 234)  # Especial

# UI Colors
WHITE = pygame.Color(248, 250, 252)  # Texto principal
LIGHT_GRAY = pygame.Color(203, 213, 225)  # Texto secundário
MEDIUM_GRAY = pygame.Color(100, 116, 139)  # Texto desabilitado
BLACK = pygame.Color(2, 6, 23)  # Texto sobre fundos claros

# Game Colors
EARTH = pygame.Color(92, 77, 65)  # Fundo do mapa - terra mais escura
EXPLOSION_ORANGE = pygame.Color(251, 146, 60)  # Explosões
BOMB_TIMER_RED = pygame.Color(220, 38, 127)  # Timer das bombas

# Legacy colors para compatibilidade
PURPLE = DARK_NAVY
ROSE = ACCENT_RED
WHITE_GRAY = LIGHT_GRAY
SOUTH_GRAY = MEDIUM_GRAY
GRAY = MEDIUM_GRAY
YELLOW = ACCENT_YELLOW
BLUE = ACCENT_BLUE
GREEN = ACCENT_GREEN


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


MODULE_SIZE = 64

# Blocks and Floors
BLOCKS_PATH = IMAGES_PATH / "blocks"

DESTROYABLE_BLOCKS: list[str] = ["caixa", "areia"]

BLOCKS: dict[GameTheme, dict[MapBlockType, pygame.Surface]] = {
    GameTheme.DESERT: {
        MapBlockType.BREAKABLE: pygame.transform.scale(
            pygame.image.load(BLOCKS_PATH / "Areia.png"), (MODULE_SIZE, MODULE_SIZE)
        ),
        MapBlockType.UNBREAKABLE: pygame.transform.scale(
            pygame.image.load(BLOCKS_PATH / "Diamante.png"), (MODULE_SIZE, MODULE_SIZE)
        ),
        MapBlockType.EMPTY: pygame.Surface((MODULE_SIZE, MODULE_SIZE), pygame.SRCALPHA),
    },
    GameTheme.SHED: {
        MapBlockType.BREAKABLE: pygame.transform.scale(
            pygame.image.load(BLOCKS_PATH / "Caixa.png"), (MODULE_SIZE, MODULE_SIZE)
        ),
        MapBlockType.UNBREAKABLE: pygame.transform.scale(
            pygame.image.load(BLOCKS_PATH / "Metal.png"), (MODULE_SIZE, MODULE_SIZE)
        ),
        MapBlockType.EMPTY: pygame.Surface((MODULE_SIZE, MODULE_SIZE), pygame.SRCALPHA),
    },
}

# Songs
SONGS_PATH = ASSETS_PATH / "songs"
SONGS: dict[GameTheme, Path] = {
    GameTheme.DESERT: SONGS_PATH / "desert_theme.mpeg",
    GameTheme.SHED: SONGS_PATH / "shed_theme.mpeg",
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
]

# Particles

PARTICLES_PATH = IMAGES_PATH / "particles"
EXPLOSION_PARTICLES: dict[ParticleType, list[pygame.Surface]] = {
    "geo": [
        pygame.transform.scale(
            pygame.image.load(PARTICLES_PATH / "core.png"),
            (MODULE_SIZE, MODULE_SIZE),
        )
    ],
    "tip": [
        pygame.transform.rotate(
            pygame.transform.scale(
                pygame.image.load(PARTICLES_PATH / "tip.png"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            angle,
        )
        for angle in range(0, 271, 90)
    ],
    "tail": [
        pygame.transform.rotate(
            pygame.transform.scale(
                pygame.image.load(PARTICLES_PATH / "tail.png"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            angle,
        )
        for angle in range(0, 271, 90)
    ],
}

# Players
CARLITOS_PATH = IMAGES_PATH / "carlitos_player"
CARLITOS: dict[PlayerDirectionState, list[pygame.Surface]] = {
    "right": [
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "horizontal_1.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "horizontal_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "horizontal_3.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
    "left": [
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(CARLITOS_PATH / "horizontal_1.png"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(CARLITOS_PATH / "horizontal_2.png"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(CARLITOS_PATH / "horizontal_3.png"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
    ],
    "down": [
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "front_1.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "front_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "front_3.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
    "up": [
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "back_1.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "back_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "back_3.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
    "stand_by": [
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "horizontal_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(CARLITOS_PATH / "horizontal_2.png"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "front_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(CARLITOS_PATH / "back_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
}

ROGERIO_PATH = IMAGES_PATH / "rogerio_player"
ROGERIO: dict[PlayerDirectionState, list[pygame.Surface]] = {
    "right": [
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "horizontal_1.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "horizontal_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "horizontal_3.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
    "left": [
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(ROGERIO_PATH / "horizontal_1.png"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(ROGERIO_PATH / "horizontal_2.png"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(ROGERIO_PATH / "horizontal_3.png"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
    ],
    "down": [
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "front_1.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "front_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "front_3.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
    "up": [
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "back_1.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "back_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "back_3.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
    "stand_by": [
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "horizontal_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.flip(
            pygame.transform.scale(
                pygame.image.load(ROGERIO_PATH / "horizontal_2.png"),
                (MODULE_SIZE, MODULE_SIZE),
            ),
            True,
            False,
        ),
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "front_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
        pygame.transform.scale(
            pygame.image.load(ROGERIO_PATH / "back_2.png"),
            (MODULE_SIZE, MODULE_SIZE),
        ),
    ],
}


PLAYERS_MAP: dict[PlayerType, dict[PlayerDirectionState, list[pygame.Surface]]] = {
    "carlitos": CARLITOS,
    "rogerio": ROGERIO,
}


class TimeManagement:
    def __init__(self, clock_time: int) -> None:
        self.last_updated = 0
        self.elapsed_time = 0
        self.time_counter = 0
        self.clock_time = clock_time

    def load(self) -> bool:
        self.elapsed_time = pygame.time.get_ticks() - self.last_updated
        self.last_updated = pygame.time.get_ticks()
        if self.elapsed_time >= self.clock_time:
            return True
        return False
