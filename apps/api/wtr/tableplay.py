"""Shared production execution seam for interactive workers and benchmarks."""

import os
from copy import deepcopy

from .agent import Agent
from .game import Tournament
from .models import TournamentConfig
from .opponents import Opponents, require_native, resolve_seeds, seat_rng
from .players import LLMPlayer, ProviderBudget
from .tracing import LangSmithExporter


def resolve_config(config, credentials=False):
    result = TournamentConfig.model_validate(config).model_dump()
    result = resolve_seeds(result)
    if result["opponents"] == "llm":
        for seat in result["seat_configs"]:
            seat["model"] = (
                seat["model"] or result["model"] or os.getenv("OPENROUTER_MODEL", "")
            )
            if not seat["model"]:
                raise ValueError(f"Choose a model for seat {seat['seat']}")
            # Operator names are display-only. Agent identities are always Player N.
            seat["name"] = seat["name"] or f"Player {seat['seat'] + 1}"
        if credentials and not os.getenv("OPENROUTER_API_KEY"):
            raise ValueError("Set OPENROUTER_API_KEY in the backend first")
    elif result["opponents"] == "pokerth":
        require_native()
    return result


class TablePlay:
    def __init__(
        self,
        table_id,
        config,
        trace_sink=None,
        transport=None,
        agent_factory=Agent,
        export_traces=True,
    ):
        self.config = resolve_config(config)
        self.game = Tournament(table_id, self.config)
        self.exporter = None
        self.policies = {}
        self.opponents = None
        self.budget = None
        if self.config["opponents"] == "llm":
            self.budget = ProviderBudget(
                self.config["llm_limits"], self.config["player_count"]
            )
            if (
                export_traces
                and os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
                and os.getenv("LANGSMITH_API_KEY")
            ):
                self.exporter = LangSmithExporter(trace_sink)
            for seat in self.config["seat_configs"]:
                index = seat["seat"]
                rng = seat_rng(self.config["hero_seed"], index)
                self.policies[index] = LLMPlayer(
                    table_id,
                    index,
                    seat,
                    self.budget,
                    seed=rng.getrandbits(64),
                    transport=transport,
                    trace_sink=trace_sink,
                    exporter=self.exporter,
                )
        else:
            self.opponents = Opponents(self.config)
            self.policies[self.game.hero_seat] = agent_factory(
                self.config["mode"],
                self.config["model"],
                seed=self.config["hero_seed"],
                trace_sink=trace_sink,
                **({"transport": transport} if transport else {}),
            )

    def observation(self):
        obs = self.game.observation()
        if self.budget is not None:
            policy = self.policies[obs["player"]]
            history = self.game.chat if policy.config["chat_enabled"] else []
            limit = policy.limits.chat_history_limit
            obs["chat"] = {
                "last_sequence": self.game.chat_sequence,
                "messages": deepcopy(history[-limit:]) if limit else [],
                "truncated": len(history) > limit
                or self.game.chat_sequence > len(self.game.chat),
            }
        return obs

    async def decide(self, observation):
        seat = observation["player"]
        if self.budget is not None or seat == self.game.hero_seat:
            result = await self.policies[seat].decide(deepcopy(observation))
            return {
                **result,
                "player": seat,
                "chat_sequence": observation.get("chat", {}).get(
                    "last_sequence", self.game.chat_sequence
                ),
            }
        return {
            "action": self.opponents.decide(observation),
            "state_version": observation["version"],
            "player": seat,
        }

    def apply(self, obs, decision):
        if (
            decision.get("player") != obs["player"]
            or decision.get("state_version") != obs["version"]
            or self.game.actor != obs["player"]
        ):
            raise ValueError("Stale or misattributed turn")
        recorded = (
            decision
            if self.budget is not None or obs["player"] == self.game.hero_seat
            else None
        )
        self.game.apply(decision["action"], obs["version"], recorded)
        if self.budget is not None:
            self.policies[obs["player"]].accepted(obs, decision)
            # Explicit public projection: never broadcast an acting player's observation.
            events = self.game.history[-120:]
            for policy in self.policies.values():
                policy.observe_public(events)
        else:
            self.opponents.observe(obs, decision["action"])

    def snapshot(self):
        return {
            **self.game.snapshot(),
            "provider_usage": self.budget.snapshot() if self.budget else None,
        }

    def close(self):
        for policy in self.policies.values():
            policy.close()
        if self.exporter:
            self.exporter.close()
