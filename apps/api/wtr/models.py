from typing import Literal
from pydantic import BaseModel, Field, model_validator


class TournamentConfig(BaseModel):
    name: str = Field(default="The opening table", min_length=1, max_length=50)
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    stack_bb: int = Field(default=50, ge=10, le=200)
    hands_per_level: int = Field(default=8, ge=2, le=100)
    payouts: Literal["70/30", "winner-take-all"] = "70/30"
    mode: Literal["heuristic", "openrouter"] = "heuristic"
    model: str = Field(default="", max_length=150, pattern=r"^[A-Za-z0-9/_.:\-]*$")
    pace: float = Field(default=1.2, ge=0.05, le=5)


class Control(BaseModel):
    action: Literal["resume", "pause", "step", "stop", "speed"]
    pace: float | None = Field(default=None, ge=0.05, le=5)

    @model_validator(mode="after")
    def speed_value(self):
        if self.action == "speed" and self.pace is None:
            raise ValueError("Speed requires pace")
        return self
