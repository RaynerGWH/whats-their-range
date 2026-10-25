from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LLMLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_calls_per_player: int = Field(default=100, ge=0, le=1000)
    max_calls_total: int = Field(default=400, ge=0, le=6000)
    max_output_tokens: int = Field(default=600, ge=64, le=2000)
    max_output_tokens_per_player: int = Field(default=60000, ge=0, le=2000000)
    max_output_tokens_total: int = Field(default=240000, ge=0, le=12000000)
    deadline_seconds: float = Field(default=10, ge=0.05, le=30)
    max_input_chars: int = Field(default=24000, ge=2000, le=64000)
    max_message_chars: int = Field(default=240, ge=1, le=500)
    chat_history_limit: int = Field(default=40, ge=0, le=100)
    memory_turns: int = Field(default=8, ge=0, le=30)


class SeatConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seat: int = Field(ge=0, le=5)
    name: str = Field(default="", max_length=40, pattern=r"^[^\x00-\x1f]*$")
    model: str = Field(default="", max_length=150, pattern=r"^[A-Za-z0-9/_.:\-]*$")
    instruction_profile: Literal["free_play"] = "free_play"
    harness: Literal["baseline"] = "baseline"
    chat_enabled: bool = True
    temperature: float = Field(default=1.0, ge=0, le=2)


class TournamentConfig(BaseModel):
    name: str = Field(default="The opening table", min_length=1, max_length=50)
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    stack_bb: int = Field(default=50, ge=10, le=200)
    hands_per_level: int = Field(default=8, ge=2, le=100)
    payouts: Literal["70/30", "winner-take-all"] = "70/30"
    mode: Literal["heuristic", "openrouter"] = "heuristic"
    opponents: Literal["legacy", "pokerth", "llm"] = "legacy"
    player_count: Literal[4, 6] = 6
    hero_seat: int = Field(default=0, ge=0, le=5)
    hero_control: Literal["human", "llm"] = "llm"
    seat_configs: list[SeatConfig] = Field(default_factory=list, max_length=6)
    llm_limits: LLMLimits = Field(default_factory=LLMLimits)
    opponent_seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    personality_seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    hero_seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    model: str = Field(default="", max_length=150, pattern=r"^[A-Za-z0-9/_.:\-]*$")
    pace: float = Field(default=1.2, ge=0.05, le=5)

    @model_validator(mode="after")
    def seats(self):
        if self.hero_seat >= self.player_count:
            raise ValueError("Hero seat must be inside the table")
        if self.opponents == "llm":
            if sorted(s.seat for s in self.seat_configs) != list(
                range(self.player_count)
            ):
                raise ValueError(
                    "LLM mode requires exactly one configuration for every seat"
                )
        elif self.hero_control != "llm":
            raise ValueError("Manual hero requires LLM opponent mode")
        elif self.seat_configs:
            raise ValueError("Seat configurations require LLM mode")
        return self


class Control(BaseModel):
    action: Literal["resume", "pause", "step", "stop", "speed", "set_hero_control"]
    pace: float | None = Field(default=None, ge=0.05, le=5)

    hero_control: Literal["human", "llm"] | None = None
    state_version: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def speed_value(self):
        if self.action == "set_hero_control" and (
            self.hero_control is None or self.state_version is None
        ):
            raise ValueError(
                "Control switch requires hero_control and observed state_version"
            )
        if self.action == "speed" and self.pace is None:
            raise ValueError("Speed requires pace")
        return self


class HeroAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_token: str = Field(min_length=16, max_length=128)
    state_version: int = Field(ge=0)
    action: str = Field(min_length=1, max_length=40)
    public_message: str | None = Field(default=None, max_length=500)
