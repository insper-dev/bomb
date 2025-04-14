import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

# Constantes do mapa
MAP_WIDTH = 15
MAP_HEIGHT = 13


class Direction(Enum):
    """Direções possíveis de movimento"""

    NONE = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class TileType(Enum):
    """Tipos de tiles no mapa"""

    EMPTY = 0
    WALL = 1  # Paredes indestrutíveis
    BREAKABLE = 2  # Paredes destrutíveis
    BOMB = 3
    EXPLOSION = 4
    POWERUP = 5


class PowerUpType(Enum):
    """Tipos de power-ups"""

    BOMB_COUNT = auto()  # Aumenta o número máximo de bombas
    BOMB_RANGE = auto()  # Aumenta o alcance da explosão
    SPEED = auto()  # Aumenta a velocidade do jogador
    KICK = auto()  # Permite chutar bombas
    PASS_WALL = auto()  # Permite passar por paredes destrutíveis


class GameStatus(Enum):
    """Status do jogo"""

    WAITING = auto()  # Aguardando jogadores conectarem
    RUNNING = auto()  # Jogo em andamento
    ENDED = auto()  # Jogo finalizado


@dataclass
class Position:
    """Posição no mapa"""

    x: float
    y: float


@dataclass
class PlayerState:
    """Estado de um jogador"""

    id: str
    position: Position
    direction: Direction = Direction.NONE
    alive: bool = True
    bomb_count: int = 1  # Bombas que o jogador pode colocar simultaneamente
    bomb_limit: int = 1  # Limite máximo de bombas
    bomb_range: int = 1  # Alcance da explosão
    speed: float = 1.0  # Multiplicador de velocidade
    score: int = 0


@dataclass
class BombState:
    """Estado de uma bomba"""

    id: str
    position: Position
    player_id: str
    timer: float  # Tempo até a explosão
    range: int  # Alcance da explosão


@dataclass
class PowerUpState:
    """Estado de um power-up"""

    id: str
    position: Position
    type: PowerUpType


@dataclass
class MapState:
    """Estado do mapa"""

    width: int = MAP_WIDTH
    height: int = MAP_HEIGHT

    tiles: list[list[TileType]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.tiles:
            self.tiles = [[TileType.EMPTY for _ in range(self.width)] for _ in range(self.height)]


@dataclass
class GameState:
    """Estado completo do jogo"""

    id: str
    status: GameStatus
    map: MapState
    players: dict[str, PlayerState]
    bombs: dict[str, BombState]
    powerups: dict[str, PowerUpState]
    start_time: float
    current_time: float
    toxic_gas_radius: float | None = None  # Para modo battle royale


# Ações dos jogadores
@dataclass
class PlayerAction:
    """Ação do jogador"""

    player_id: str
    action_type: str  # "move", "place_bomb", etc.
    data: dict[str, Any]
    timestamp: float

    @staticmethod
    def create_move_action(player_id: str, direction: Direction) -> "PlayerAction":
        """Cria uma ação de movimento"""
        return PlayerAction(
            player_id=player_id,
            action_type="move",
            data={"direction": direction.name},
            timestamp=time.time(),
        )

    @staticmethod
    def create_place_bomb_action(player_id: str, position: Position) -> "PlayerAction":
        """Cria uma ação de colocação de bomba"""
        return PlayerAction(
            player_id=player_id,
            action_type="place_bomb",
            data={"position": {"x": position.x, "y": position.y}},
            timestamp=time.time(),
        )


# Eventos do jogo
@dataclass
class GameEvent:
    """Evento do jogo"""

    event_type: str  # "explosion", "player_hit", "game_end", etc.
    data: dict[str, Any]
    timestamp: float

    @staticmethod
    def create_explosion_event(
        bomb_id: str,
        position: Position,
        affected_positions: list[Position],
        destroyed_walls: list[Position],
        affected_players: list[str],
    ) -> "GameEvent":
        """Cria um evento de explosão"""
        return GameEvent(
            event_type="explosion",
            data={
                "bomb_id": bomb_id,
                "position": {"x": position.x, "y": position.y},
                "affected_positions": [{"x": p.x, "y": p.y} for p in affected_positions],
                "destroyed_walls": [{"x": p.x, "y": p.y} for p in destroyed_walls],
                "affected_players": affected_players,
            },
            timestamp=time.time(),
        )

    @staticmethod
    def create_player_hit_event(player_id: str, source: str) -> "GameEvent":
        """Cria um evento de jogador atingido"""
        return GameEvent(
            event_type="player_hit",
            data={"player_id": player_id, "source": source},
            timestamp=time.time(),
        )

    @staticmethod
    def create_game_end_event(reason: str, winner_id: str | None) -> "GameEvent":
        """Cria um evento de fim de jogo"""
        return GameEvent(
            event_type="game_end",
            data={"reason": reason, "winner_id": winner_id},
            timestamp=time.time(),
        )
