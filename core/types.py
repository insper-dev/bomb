from pathlib import Path
from typing import Literal

type Coordinate = tuple[int, int]
type Thickness = int
type IsFocused = bool
type IsDisabled = bool
type FontPath = Path
type ComponentType = Literal["button", "text", "input", "state"]
type ComponentSize = Literal["sm", "md", "lg"]
type ComponentVariant = Literal["standard", "primary", "secondary", "outline"]
type FontStyle = Literal["normal", "bold", "italic", "bold_italic"]
type FontSize = Literal["standard", "title", "subtitle", "text"]
type ParticleType = Literal["geo", "tip", "tail"]
type PlayerDirectionState = Literal["up", "down", "left", "right", "stand_by"]
type PlayerType = Literal["carlitos", "rogerio"]

__all__ = [
    "ComponentSize",
    "ComponentType",
    "ComponentVariant",
    "Coordinate",
    "FontPath",
    "FontSize",
    "FontStyle",
    "IsDisabled",
    "IsFocused",
    "ParticleType",
    "PlayerDirectionState",
    "PlayerType",
    "Thickness",
]
