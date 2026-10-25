"""Local policies receive only Tournament.observation(), never the engine."""

from dataclasses import dataclass
from importlib import import_module
import random
from typing import Protocol

from wtr.agent import assess, baseline


class Policy(Protocol):
    def decide(self, observation: dict) -> dict:
        """Return action and state_version. Async implementations are also accepted."""
        ...


@dataclass(frozen=True)
class PolicySpec:
    name: str = "heuristic"
    version: str = "skeleton-0fe9596-v1"
    factory: str = "wtr.evaluation.policies:Heuristic"

    def __post_init__(self):
        if not self.name or not self.version or ":" not in self.factory:
            raise ValueError("Policy requires a name, version and module:factory")

    def build(self, seed: int) -> Policy:
        module, name = self.factory.split(":", 1)
        policy = getattr(import_module(module), name)(seed)
        if not callable(getattr(policy, "decide", None)):
            raise TypeError("Policy factory must return an object with decide(observation)")
        return policy


class Heuristic:
    """Same assess/baseline and RNG offset as Agent(mode='heuristic')."""

    def __init__(self, seed):
        self.rng = random.Random(seed + 991)

    def decide(self, observation):
        metrics = assess({"observation": observation})["metrics"]
        return {
            "action": baseline(observation, metrics, self.rng),
            "state_version": observation["version"],
        }


class CheckCall:
    def __init__(self, seed):
        pass

    def decide(self, observation):
        action = next(a for a in observation["legal"] if a["kind"] == "call")
        return {"action": action["key"], "state_version": observation["version"]}


class Shove(CheckCall):
    """Choose maximum legal raise-to; check/call if raising is unavailable."""

    def decide(self, observation):
        raises = [a for a in observation["legal"] if a["kind"] == "raise"]
        if not raises:
            return super().decide(observation)
        return {
            "action": max(raises, key=lambda a: a["amount"])["key"],
            "state_version": observation["version"],
        }


POLICIES = {
    "heuristic": PolicySpec(),
    "check-call": PolicySpec("check-call", "1", "wtr.evaluation.policies:CheckCall"),
    "shove": PolicySpec("shove", "1", "wtr.evaluation.policies:Shove"),
}
SCENARIOS = ("standard", "single-shover", "repeated-shove")


def opponent_action(observation, scenario, profile, rng):
    if scenario == "repeated-shove" or (
        scenario == "single-shover" and observation["player"] == 1
    ):
        return Shove(0).decide(observation)["action"]
    metrics = assess({"observation": observation})["metrics"]
    return baseline(observation, metrics, rng, profile)
