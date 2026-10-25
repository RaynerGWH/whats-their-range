import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..models import TournamentConfig
from ..players import HARNESS_VERSION, PROMPT_VERSION, prompt_hash
from ..tableplay import resolve_config


class SeedSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    split: Literal["development", "held_out"]
    deck: int = Field(ge=0, le=2**31 - 1)
    policy: int = Field(ge=0, le=2**31 - 1)


class StopRules(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_hands: int = Field(default=300, ge=1, le=1000)
    max_actions: int = Field(default=5000, ge=1, le=20000)
    timeout_seconds: float = Field(default=60, ge=0.1, le=300)


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["llm-benchmark-v1"] = "llm-benchmark-v1"
    name: str = Field(min_length=1, max_length=100)
    table: TournamentConfig
    seeds: list[SeedSet] = Field(min_length=1, max_length=20)
    rotations: list[int] = Field(
        default_factory=lambda: list(range(6)), min_length=1, max_length=6
    )
    presets: list[Literal["same_model", "chat_disabled", "model_swap"]] = Field(
        default_factory=lambda: ["same_model", "chat_disabled", "model_swap"],
        min_length=1,
        max_length=3,
    )
    swap_model: str = Field(default="", max_length=150, pattern=r"^[A-Za-z0-9/_.:\-]*$")
    stopping: StopRules = Field(default_factory=StopRules)

    @model_validator(mode="after")
    def validate_experiment(self):
        if self.table.opponents != "llm" or self.table.hero_control != "llm":
            raise ValueError(
                "Autonomous benchmarks require LLM mode and hero_control=llm throughout"
            )
        if any(not 0 <= r < self.table.player_count for r in self.rotations) or len(
            set(self.rotations)
        ) != len(self.rotations):
            raise ValueError("Rotations must be unique valid seat offsets")
        if len(set(self.presets)) != len(self.presets):
            raise ValueError("Presets must be unique")
        if len({s.deck for s in self.seeds}) != len(self.seeds) or len(
            {s.policy for s in self.seeds}
        ) != len(self.seeds):
            raise ValueError("Independent seed sets must not repeat across splits")
        if len(self.seeds) * len(self.rotations) * len(self.presets) > 120:
            raise ValueError("This small runner supports at most 120 runs per manifest")
        if "model_swap" in self.presets and not self.swap_model:
            raise ValueError("model_swap requires swap_model")
        # Do not inherit environment model defaults in reproducible experiments.
        models = {s.model or self.table.model for s in self.table.seat_configs}
        if len(models) != 1 or "" in models:
            raise ValueError("The control must specify one explicit shared model")
        if "model_swap" in self.presets and self.swap_model in models:
            raise ValueError("swap_model must differ from the control model")
        settings = {
            (s.instruction_profile, s.harness, s.chat_enabled, s.temperature)
            for s in self.table.seat_configs
        }
        if len(settings) != 1 or not all(
            s.chat_enabled for s in self.table.seat_configs
        ):
            raise ValueError(
                "Control seats must share neutral settings with chat enabled"
            )
        return self


def expand(manifest):
    manifest = Manifest.model_validate(manifest)
    runs = []
    for seed in manifest.seeds:
        for preset in manifest.presets:
            for rotation in manifest.rotations:
                cfg = manifest.table.model_dump()
                cfg.update(
                    seed=seed.deck,
                    hero_seed=seed.policy,
                    opponent_seed=seed.policy,
                    personality_seed=seed.policy,
                )
                count, original_hero = cfg["player_count"], cfg["hero_seat"]
                cfg["hero_seat"] = (original_hero + rotation) % count
                for seat in cfg["seat_configs"]:
                    original = seat["seat"]
                    seat["seat"] = (original + rotation) % count
                    seat["name"] = f"Player {seat['seat'] + 1}"
                    if preset == "chat_disabled":
                        seat["chat_enabled"] = False
                    if preset == "model_swap" and original == original_hero:
                        seat["model"] = manifest.swap_model
                cfg["seat_configs"].sort(key=lambda s: s["seat"])
                cfg = resolve_config(cfg)
                runs.append(
                    {
                        "run": len(runs),
                        "split": seed.split,
                        "seed_set": seed.model_dump(),
                        "preset": preset,
                        "rotation": rotation,
                        "config": cfg,
                        "stopping": manifest.stopping.model_dump(),
                        "player_versions": [
                            {
                                "seat": s["seat"],
                                "prompt_version": PROMPT_VERSION,
                                "prompt_sha256": prompt_hash(s["chat_enabled"]),
                                "harness_version": HARNESS_VERSION,
                            }
                            for s in cfg["seat_configs"]
                        ],
                    }
                )
    return runs


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
