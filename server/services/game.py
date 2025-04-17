"""
Game Service - Handles game instances and game logic
"""

import asyncio
import json
import logging
import random
import time
import uuid

from fastapi import WebSocket

from core.models.game import (
    BombState,
    Direction,
    GameEvent,
    GameState,
    GameStatus,
    MapState,
    PlayerState,
    Position,
    PowerUpState,
    PowerUpType,
    TileType,
)

logger = logging.getLogger(__name__)

# Game settings
PLAYER_SPEED = 0.1
BOMB_TIMER = 3.0  # seconds
UPDATE_RATE = 1 / 30  # 30 FPS


class Game:
    """Represents a game instance."""

    def __init__(self, game_id: str, player_ids: list[str]) -> None:
        """Initialize a new game instance.

        Args:
            game_id: Unique identifier for the game
            player_ids: List of player IDs participating in the game
        """
        self.id = game_id
        self.players = player_ids
        self.connections: dict[str, WebSocket] = {}
        # First create a temporary map state to use in initialization
        temp_map = self._generate_map()
        # Then initialize the game state using the map
        self.state = self._initialize_game_state(game_id, player_ids, temp_map)
        self.started = False
        self.ended = False
        self.last_update_time = time.time()
        self.game_loop_task: asyncio.Task | None = None
        self.lock = asyncio.Lock()

    def _generate_map(self) -> MapState:
        """Generate a game map with walls and destructible blocks."""
        map_state = MapState()

        # Configure permanent walls (in alternating positions)
        for y in range(map_state.height):
            for x in range(map_state.width):
                if x % 2 == 1 and y % 2 == 1:
                    map_state.tiles[y][x] = TileType.WALL

        # Add destructible blocks (with some randomness)
        for y in range(map_state.height):
            for x in range(map_state.width):
                # Skip positions with permanent walls
                if map_state.tiles[y][x] == TileType.WALL:
                    continue

                # Skip initial areas for players
                if (
                    (x < 2 and y < 2)
                    or (x >= map_state.width - 2 and y < 2)
                    or (x < 2 and y >= map_state.height - 2)
                    or (x >= map_state.width - 2 and y >= map_state.height - 2)
                ):
                    continue

                # 40% chance to generate a destructible block
                if random.random() < 0.4:
                    map_state.tiles[y][x] = TileType.BREAKABLE

        return map_state

    def _get_start_positions(
        self, num_players: int, map_width: int, map_height: int
    ) -> list[Position]:
        """Get initial positions for players.

        Args:
            num_players: Number of players
            map_width: Width of the map
            map_height: Height of the map

        Returns:
            List of starting positions
        """
        # Common positions are in the corners
        positions = [
            Position(1, 1),  # Top-left
            Position(map_width - 2, map_height - 2),  # Bottom-right
            Position(map_width - 2, 1),  # Top-right
            Position(1, map_height - 2),  # Bottom-left
        ]

        # Return only the number of positions needed
        return positions[:num_players]

    def _initialize_game_state(
        self, game_id: str, player_ids: list[str], map_state: MapState
    ) -> GameState:
        """Initialize the game state with default values.

        Args:
            game_id: Unique identifier for the game
            player_ids: List of player IDs
            map_state: The generated map state

        Returns:
            Initialized game state
        """
        player_states = {}

        # Assign initial positions to players
        start_positions = self._get_start_positions(
            len(player_ids), map_state.width, map_state.height
        )

        for i, player_id in enumerate(player_ids):
            position = start_positions[i]
            player_states[player_id] = PlayerState(id=player_id, position=position)

        return GameState(
            id=game_id,
            status=GameStatus.WAITING,
            map=map_state,
            players=player_states,
            bombs={},
            powerups={},
            start_time=time.time(),
            current_time=time.time(),
        )

    async def add_player_connection(self, player_id: str, websocket: WebSocket) -> bool:
        """Add a player connection to the game.

        Args:
            player_id: ID of the player
            websocket: WebSocket connection

        Returns:
            True if the player was added, False otherwise
        """
        try:
            async with asyncio.timeout(2.0):
                async with self.lock:
                    if player_id not in self.players:
                        logger.warning(f"Player {player_id} is not part of game {self.id}")
                        return False

                    self.connections[player_id] = websocket

                    # If all players are connected, start the game
                    if len(self.connections) == len(self.players) and not self.started:
                        try:
                            await self.start_game()
                        except asyncio.CancelledError:
                            logger.warning(f"Game {self.id} start cancelled during shutdown")
                            return False

                    return True
        except (TimeoutError, asyncio.CancelledError):
            logger.warning(f"Timeout or cancellation adding player {player_id} to game {self.id}")
            if player_id in self.connections:
                self.connections.pop(player_id, None)
            return False

    async def remove_player_connection(self, player_id: str) -> None:
        """Remove a player connection from the game.

        Args:
            player_id: ID of the player
        """
        try:
            # Use a timeout to avoid hanging
            async with asyncio.timeout(2.0):
                async with self.lock:
                    if player_id in self.connections:
                        self.connections.pop(player_id)

                    # If there are no more players, end the game
                    if len(self.connections) == 0:
                        await self.end_game("All players disconnected")
        except (TimeoutError, asyncio.CancelledError):
            logger.warning(
                f"Timeout or cancellation removing player {player_id} from game {self.id}"
            )
            if player_id in self.connections:
                self.connections.pop(player_id)

    async def start_game(self) -> None:
        """Start the game."""
        try:
            async with asyncio.timeout(2.0):
                async with self.lock:
                    if self.started or self.ended:
                        return

                    self.state.status = GameStatus.RUNNING
                    self.started = True
                    self.state.start_time = time.time()

                    # Notify all players that the game has started
                    try:
                        await self.broadcast_event(
                            GameEvent(
                                event_type="game_start",
                                data=self._get_init_state_dict(),
                                timestamp=time.time(),
                            )
                        )
                    except Exception as e:
                        logger.error(f"Error broadcasting game start: {e}")
                        self.started = False
                        return

                    # Start the game loop
                    self.game_loop_task = asyncio.create_task(self.game_loop())

                    logger.info(f"Game {self.id} started with players: {self.players}")
        except (TimeoutError, asyncio.CancelledError):
            logger.warning(f"Timeout or cancellation starting game {self.id}")
            self.started = False
            if self.game_loop_task:
                self.game_loop_task.cancel()

    async def end_game(self, reason: str) -> None:
        """End the game.

        Args:
            reason: Reason for ending the game
        """
        try:
            async with asyncio.timeout(2.0):
                async with self.lock:
                    if self.ended:
                        return

                    self.state.status = GameStatus.ENDED
                    self.ended = True

                    # Stop the game loop
                    if self.game_loop_task and not self.game_loop_task.done():
                        self.game_loop_task.cancel()
                        try:
                            await asyncio.wait_for(self.game_loop_task, timeout=1.0)
                        except (TimeoutError, asyncio.CancelledError):
                            pass

                    # Clear connections immediately
                    self.connections.clear()

                    # Determine the winner
                    winner_id = self._determine_winner()

                    # Notify all players that the game has ended
                    try:
                        await self.broadcast_event(
                            GameEvent.create_game_end_event(reason, winner_id)
                        )
                    except Exception as e:
                        logger.error(f"Error broadcasting game end: {e}")

                    logger.info(f"Game {self.id} ended: {reason}")
        except (TimeoutError, asyncio.CancelledError):
            logger.warning(f"Timeout or cancellation ending game {self.id}")
            # Force cleanup
            self.connections.clear()
            if self.game_loop_task:
                self.game_loop_task.cancel()

    def _determine_winner(self) -> str | None:
        """Determine the winner of the game.

        Returns:
            ID of the winner or None in case of a tie
        """
        alive_players = [
            player_id for player_id, state in self.state.players.items() if state.alive
        ]

        if len(alive_players) == 1:
            return alive_players[0]
        elif len(alive_players) == 0:
            return None  # Tie
        else:
            # If there are multiple players alive, compare scores
            best_score = -1
            best_player = None

            for player_id, state in self.state.players.items():
                if state.score > best_score:
                    best_score = state.score
                    best_player = player_id

            return best_player

    async def game_loop(self) -> None:
        """Main game loop that updates the state."""
        try:
            while self.started and not self.ended:
                # Calculate delta time
                current_time = time.time()
                delta_time = current_time - self.last_update_time
                self.last_update_time = current_time
                self.state.current_time = current_time

                async with self.lock:
                    # Update bombs
                    await self._update_bombs(delta_time)

                    # Check collisions with power-ups
                    await self._check_powerup_collisions()

                    # Check end game conditions
                    if self._check_game_end_condition():
                        await self.end_game("End game conditions reached")
                        break

                    # Send state update to all players
                    await self.broadcast_state_update()

                # Sleep to maintain update rate
                await asyncio.sleep(UPDATE_RATE)
        except asyncio.CancelledError:
            # Game was cancelled, exit gracefully
            logger.info(f"Game loop for game {self.id} cancelled")
        except Exception as e:
            logger.error(f"Error in game loop: {e}")
            await self.end_game(f"Internal error: {e!s}")

    async def _update_bombs(self, delta_time: float) -> None:
        """Update bomb timers and handle explosions.

        Args:
            delta_time: Time elapsed since last update
        """
        exploding_bombs = []

        # Update bomb timers
        for bomb_id, bomb in list(self.state.bombs.items()):
            bomb.timer -= delta_time

            if bomb.timer <= 0:
                exploding_bombs.append(bomb)
                del self.state.bombs[bomb_id]

        # Handle explosions
        for bomb in exploding_bombs:
            await self._handle_explosion(bomb)

    async def _handle_explosion(self, bomb: BombState) -> None:
        """Handle a bomb explosion.

        Args:
            bomb: Bomb that exploded
        """
        # Calculate affected tiles
        affected_positions = []
        destroyed_walls = []
        affected_players = []

        # Helper to check explosion in a direction
        def check_direction(dx, dy) -> None:
            for i in range(1, bomb.range + 1):
                x = int(bomb.position.x + dx * i)
                y = int(bomb.position.y + dy * i)

                # Check boundaries
                if x < 0 or x >= self.state.map.width or y < 0 or y >= self.state.map.height:
                    break

                # Check tile type
                tile = self.state.map.tiles[y][x]
                if tile == TileType.WALL:
                    break  # Stop at permanent walls
                elif tile == TileType.BREAKABLE:
                    destroyed_walls.append(Position(x, y))
                    self.state.map.tiles[y][x] = TileType.EMPTY

                    # Chance to generate power-up
                    if random.random() < 0.3:  # 30% chance
                        self._spawn_powerup(x, y)

                    break  # Stop at destructible walls after destroying them

                affected_positions.append(Position(x, y))

                # Check if players are affected
                for player_id, player in self.state.players.items():
                    if player.alive:
                        px, py = int(player.position.x), int(player.position.y)
                        if px == x and py == y:
                            affected_players.append(player_id)

        # Check in all four directions
        check_direction(1, 0)  # Right
        check_direction(-1, 0)  # Left
        check_direction(0, 1)  # Down
        check_direction(0, -1)  # Up

        # Add explosion tiles to the map temporarily
        for pos in affected_positions:
            x, y = int(pos.x), int(pos.y)
            self.state.map.tiles[y][x] = TileType.EXPLOSION

        # Handle affected players
        for player_id in affected_players:
            player = self.state.players[player_id]
            player.alive = False  # Player dies from explosion

            # Notify about the hit
            await self.broadcast_event(GameEvent.create_player_hit_event(player_id, "bomb"))

        # Create explosion event
        await self.broadcast_event(
            GameEvent.create_explosion_event(
                bomb_id=bomb.id,
                position=bomb.position,
                affected_positions=affected_positions,
                destroyed_walls=destroyed_walls,
                affected_players=affected_players,
            )
        )

        # Schedule removal of explosion tiles
        asyncio.create_task(self._remove_explosion_tiles(affected_positions))  # noqa: RUF006

    def _spawn_powerup(self, x: int, y: int) -> None:
        """Generate a power-up at the specified position.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        # Choose a random power-up type
        powerup_types = list(PowerUpType)
        powerup_type = random.choice(powerup_types)

        # Create the power-up
        powerup_id = str(uuid.uuid4())
        powerup = PowerUpState(id=powerup_id, position=Position(x, y), type=powerup_type)

        # Add to game state
        self.state.powerups[powerup_id] = powerup

    async def _check_powerup_collisions(self) -> None:
        """Check collisions between players and power-ups."""
        for player_id, player in self.state.players.items():
            if not player.alive:
                continue

            player_x, player_y = int(player.position.x), int(player.position.y)

            for powerup_id, powerup in list(self.state.powerups.items()):
                powerup_x, powerup_y = int(powerup.position.x), int(powerup.position.y)

                if player_x == powerup_x and player_y == powerup_y:
                    # Player collided with power-up
                    await self._apply_powerup(player, powerup)
                    del self.state.powerups[powerup_id]

                    # Notify power-up collection
                    await self.broadcast_event(
                        GameEvent(
                            event_type="powerup_collected",
                            data={
                                "player_id": player_id,
                                "powerup_id": powerup_id,
                                "powerup_type": powerup.type.name,
                            },
                            timestamp=time.time(),
                        )
                    )

    async def _apply_powerup(self, player: PlayerState, powerup: PowerUpState) -> None:
        """Apply a power-up to a player.

        Args:
            player: Player to apply the power-up to
            powerup: Power-up to apply
        """
        if powerup.type == PowerUpType.BOMB_COUNT:
            player.bomb_limit += 1
        elif powerup.type == PowerUpType.BOMB_RANGE:
            player.bomb_range += 1
        elif powerup.type == PowerUpType.SPEED:
            player.speed += 0.3  # Increase speed by 30%

    async def _remove_explosion_tiles(self, positions: list[Position]) -> None:
        """Remove explosion tiles after a delay.

        Args:
            positions: Positions of explosion tiles
        """
        await asyncio.sleep(0.5)  # Duration of explosion animation

        async with self.lock:
            for pos in positions:
                x, y = int(pos.x), int(pos.y)
                if (
                    0 <= x < self.state.map.width
                    and 0 <= y < self.state.map.height
                    and self.state.map.tiles[y][x] == TileType.EXPLOSION
                ):
                    self.state.map.tiles[y][x] = TileType.EMPTY

    def _check_game_end_condition(self) -> bool:
        """Check if the game should end.

        Returns:
            True if the game should end, False otherwise
        """
        # Count alive players
        alive_count = sum(1 for player in self.state.players.values() if player.alive)

        # If only one or no player is alive, the game ends
        return alive_count <= 1

    def _get_init_state_dict(self) -> dict:
        """Get the initial state to send to clients when they connect.

        Returns:
            Dictionary representation of the initial state
        """
        return {
            "game_id": self.state.id,
            "map": {
                "width": self.state.map.width,
                "height": self.state.map.height,
                "tiles": [[tile.value for tile in row] for row in self.state.map.tiles],
            },
            "players": {
                player_id: {
                    "id": player.id,
                    "position": {"x": player.position.x, "y": player.position.y},
                    "direction": player.direction.name,
                    "alive": player.alive,
                    "bomb_count": player.bomb_count,
                    "bomb_limit": player.bomb_limit,
                    "bomb_range": player.bomb_range,
                    "speed": player.speed,
                    "score": player.score,
                }
                for player_id, player in self.state.players.items()
            },
            "start_time": self.state.start_time,
        }

    def _get_state_update_dict(self) -> dict:
        """Get a minimal state update to send to clients periodically.

        Returns:
            Dictionary representation of the state update
        """
        return {
            "type": "state_update",
            "data": {
                "players": {
                    player_id: {
                        "position": {"x": player.position.x, "y": player.position.y},
                        "direction": player.direction.name,
                        "alive": player.alive,
                    }
                    for player_id, player in self.state.players.items()
                },
                "bombs": {
                    bomb_id: {
                        "position": {"x": bomb.position.x, "y": bomb.position.y},
                        "timer": bomb.timer,
                    }
                    for bomb_id, bomb in self.state.bombs.items()
                },
                "powerups": {
                    powerup_id: {
                        "position": {"x": powerup.position.x, "y": powerup.position.y},
                        "type": powerup.type.name,
                    }
                    for powerup_id, powerup in self.state.powerups.items()
                },
                "current_time": self.state.current_time,
            },
            "timestamp": time.time(),
        }

    async def broadcast_state_update(self) -> None:
        """Broadcast a state update to all connected players."""
        update = self._get_state_update_dict()
        await self.broadcast_message(update)

    async def broadcast_event(self, event: GameEvent) -> None:
        """Broadcast a game event to all connected players.

        Args:
            event: Event to broadcast
        """
        event_dict = {"type": event.event_type, "data": event.data, "timestamp": event.timestamp}
        await self.broadcast_message(event_dict)

    async def broadcast_message(self, message: dict) -> None:
        """Send a message to all connected players.

        Args:
            message: Message to send
        """
        if not self.connections:
            return

        message_str = json.dumps(message)

        for player_id, websocket in list(self.connections.items()):
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message to player {player_id}: {e}")
                await self.remove_player_connection(player_id)

    async def handle_player_action(self, player_id: str, action_data: dict) -> None:
        """Handle a player action.

        Args:
            player_id: ID of the player
            action_data: Action data
        """
        if player_id not in self.players or not self.started or self.ended:
            return

        player = self.state.players.get(player_id)
        if not player or not player.alive:
            return

        action_type = action_data.get("type")
        data = action_data.get("data", {})

        async with self.lock:
            if action_type == "move":
                await self._handle_move_action(player, data)
            elif action_type == "place_bomb":
                await self._handle_place_bomb_action(player, data)

    async def _handle_move_action(self, player: PlayerState, data: dict) -> None:
        """Handle a player move action.

        Args:
            player: Player to move
            data: Move data
        """
        try:
            direction_name = data.get("direction")
            if not direction_name:
                return

            direction = Direction[direction_name]
            player.direction = direction

            # Update position based on direction and player speed
            dx, dy = 0, 0
            if direction == Direction.UP:
                dy = -PLAYER_SPEED * player.speed
            elif direction == Direction.DOWN:
                dy = PLAYER_SPEED * player.speed
            elif direction == Direction.LEFT:
                dx = -PLAYER_SPEED * player.speed
            elif direction == Direction.RIGHT:
                dx = PLAYER_SPEED * player.speed

            # Calculate new position
            new_x = player.position.x + dx
            new_y = player.position.y + dy

            # Check boundaries and collisions
            if self._is_valid_position(new_x, new_y):
                player.position.x = new_x
                player.position.y = new_y

            # Movement broadcasting is handled by the state update
        except Exception as e:
            logger.error(f"Error handling move action: {e}")

    async def _handle_place_bomb_action(self, player: PlayerState, data: dict) -> None:
        """Handle a player place bomb action.

        Args:
            player: Player placing the bomb
            data: Bomb data
        """
        try:
            # Check if the player can place more bombs
            active_bombs = sum(
                1 for bomb in self.state.bombs.values() if bomb.player_id == player.id
            )
            if active_bombs >= player.bomb_limit:
                return

            # Round position to grid
            x = round(player.position.x)
            y = round(player.position.y)

            # Check if a bomb already exists at this position
            for bomb in self.state.bombs.values():
                if int(bomb.position.x) == x and int(bomb.position.y) == y:
                    return

            # Create new bomb
            bomb_id = str(uuid.uuid4())
            bomb = BombState(
                id=bomb_id,
                position=Position(x, y),
                player_id=player.id,
                timer=BOMB_TIMER,
                range=player.bomb_range,
            )

            # Add bomb to game state
            self.state.bombs[bomb_id] = bomb

            # Broadcast bomb placement
            await self.broadcast_event(
                GameEvent(
                    event_type="bomb_placed",
                    data={
                        "bomb_id": bomb_id,
                        "position": {"x": x, "y": y},
                        "player_id": player.id,
                        "timer": bomb.timer,
                        "range": bomb.range,
                    },
                    timestamp=time.time(),
                )
            )
        except Exception as e:
            logger.error(f"Error handling place bomb action: {e}")

    def _is_valid_position(self, x: float, y: float) -> bool:
        """Check if a position is valid (within bounds and not a wall).

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if the position is valid, False otherwise
        """
        # Check boundaries
        if x < 0 or x >= self.state.map.width or y < 0 or y >= self.state.map.height:
            return False

        # Check walls (convert to integer grid position)
        grid_x = int(x)
        grid_y = int(y)

        tile = self.state.map.tiles[grid_y][grid_x]
        return tile not in (TileType.WALL, TileType.BREAKABLE)


class GameService:
    """Service to manage game instances."""

    _instance = None

    def __new__(cls) -> "GameService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        # Active games
        self.games: dict[str, Game] = {}
        # Player to game mapping
        self.player_game_map: dict[str, str] = {}
        # Lock for thread-safe access
        self.lock = asyncio.Lock()
        # Active cleanup tasks
        self.cleanup_tasks: list[asyncio.Task] = []

        self._initialized = True
        logger.info("Game service initialized")

    async def force_cleanup(self) -> None:
        """Force cleanup of all games and connections during shutdown."""
        try:
            async with asyncio.timeout(2.0):
                async with self.lock:
                    # Cancel all cleanup tasks
                    for task in self.cleanup_tasks:
                        if not task.done():
                            task.cancel()

                    # Force end all games
                    for game in list(self.games.values()):
                        if not game.ended:
                            try:
                                await game.end_game("Server shutdown")
                            except Exception as e:
                                logger.error(f"Error ending game {game.id}: {e}")
                                # Force cleanup if ending fails
                                game.connections.clear()
                                if game.game_loop_task:
                                    game.game_loop_task.cancel()

                    # Clear all games and mappings
                    self.games.clear()
                    self.player_game_map.clear()
                    self.cleanup_tasks.clear()

        except (TimeoutError, asyncio.CancelledError):
            logger.warning("Timeout or cancellation during game service cleanup")
            # Force cleanup in case of timeout
            self.games.clear()
            self.player_game_map.clear()
            self.cleanup_tasks.clear()

    async def create_game(self, player_ids: list[str]) -> str:
        """Create a new game instance for the specified players.

        Args:
            player_ids: List of player IDs

        Returns:
            ID of the created game
        """
        async with self.lock:
            game_id = str(uuid.uuid4())

            game = Game(game_id, player_ids)
            self.games[game_id] = game

            # Update player to game mapping
            for player_id in player_ids:
                self.player_game_map[player_id] = game_id

            logger.info(f"Game {game_id} created for players: {player_ids}")
            return game_id

    def get_game(self, game_id: str) -> Game | None:
        """Get a game instance by ID.

        Args:
            game_id: ID of the game

        Returns:
            Game instance or None if not found
        """
        return self.games.get(game_id)

    def get_player_game(self, player_id: str) -> Game | None:
        """Get the game instance a player is in.

        Args:
            player_id: ID of the player

        Returns:
            Game instance or None if not found
        """
        game_id = self.player_game_map.get(player_id)
        if game_id:
            return self.games.get(game_id)
        return None

    async def add_player_connection(
        self, player_id: str, game_id: str, websocket: WebSocket
    ) -> bool:
        """Add a player connection to a game.

        Args:
            player_id: ID of the player
            game_id: ID of the game
            websocket: WebSocket connection

        Returns:
            True if the player was added, False otherwise
        """
        game = self.games.get(game_id)
        if not game:
            logger.warning(f"Game {game_id} not found")
            return False

        return await game.add_player_connection(player_id, websocket)

    async def remove_player_connection(self, player_id: str) -> None:
        """Remove a player connection from their game.

        Args:
            player_id: ID of the player
        """
        async with self.lock:
            game = self.get_player_game(player_id)
            if game:
                await game.remove_player_connection(player_id)

                # If the game has ended, clean up
                if game.ended:
                    await self._cleanup_game(game.id)

    async def handle_player_action(self, player_id: str, action: dict) -> None:
        """Handle a player action in their game.

        Args:
            player_id: ID of the player
            action: Action data
        """
        game = self.get_player_game(player_id)
        if game:
            await game.handle_player_action(player_id, action)

    async def _cleanup_game(self, game_id: str) -> None:
        """Clean up a completed game.

        Args:
            game_id: ID of the game
        """
        cleanup_task = asyncio.create_task(self._do_cleanup_game(game_id))
        self.cleanup_tasks.append(cleanup_task)
        try:
            await cleanup_task
        except asyncio.CancelledError:
            logger.warning(f"Game cleanup cancelled for game {game_id}")

    async def _do_cleanup_game(self, game_id: str) -> None:
        """Internal method to clean up a game with timeout.

        Args:
            game_id: ID of the game
        """
        try:
            async with asyncio.timeout(2.0):
                async with self.lock:
                    game = self.games.pop(game_id, None)
                    if game:
                        # Remove player to game mappings
                        for player_id in game.players:
                            self.player_game_map.pop(player_id, None)

                        logger.info(f"Game {game_id} cleaned up")
        except (TimeoutError, asyncio.CancelledError):
            logger.warning(f"Timeout or cancellation during game cleanup for game {game_id}")
            # Force cleanup even if timeout
            if game_id in self.games:
                game = self.games.pop(game_id)
                for player_id in game.players:
                    self.player_game_map.pop(player_id, None)


# Initialize singleton instance
game_service = GameService()
