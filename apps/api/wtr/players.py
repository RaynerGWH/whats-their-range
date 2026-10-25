"""Per-seat neutral LLM players. No other-seat configuration enters this module's prompts."""

import asyncio
import hashlib
import json
import os
import random
import time
from copy import deepcopy
from pathlib import Path
from typing import Protocol

import httpx

from .agent import assess, baseline
from .models import LLMLimits
from .tracing import (
    Trace,
    current_trace,
    private_observation,
    public_events,
    usage_from_provider,
)

PROMPT_VERSION = "free_play-v1"
HARNESS_VERSION = "baseline-v1"
PROMPT = (Path(__file__).with_name("prompts") / "free_play_v1.txt").read_text()
CHAT_ON = "Table talk is enabled. You may attach one public message to your action, within the supplied message length limit, or use null to stay silent. Speaking is optional."
CHAT_OFF = "Table talk is disabled. You receive no message contents. Return null for public_message."


def instruction(chat_enabled):
    return PROMPT + "\n" + (CHAT_ON if chat_enabled else CHAT_OFF)


def prompt_hash(chat_enabled):
    return hashlib.sha256(instruction(chat_enabled).encode()).hexdigest()


class PlayerPolicy(Protocol):
    async def decide(self, observation: dict) -> dict: ...
    def accepted(self, observation: dict, decision: dict) -> None: ...
    def observe_public(self, events: list[dict]) -> None: ...
    def close(self) -> None: ...


class ProviderBudget:
    """Reserve output capacity before every attempt, including failures. No retries."""

    def __init__(self, limits, count):
        self.limits = LLMLimits.model_validate(limits)
        self.seats = [
            {
                "attempts": 0,
                "reserved_output_tokens": 0,
                "fallbacks": 0,
                "budget_exhausted": False,
                "usage": [],
            }
            for _ in range(count)
        ]

    def reserve(self, seat):
        s, limit = self.seats[seat], self.limits
        calls = sum(p["attempts"] for p in self.seats)
        tokens = sum(p["reserved_output_tokens"] for p in self.seats)
        if (
            s["attempts"] >= limit.max_calls_per_player
            or calls >= limit.max_calls_total
            or s["reserved_output_tokens"] + limit.max_output_tokens
            > limit.max_output_tokens_per_player
            or tokens + limit.max_output_tokens > limit.max_output_tokens_total
        ):
            s["budget_exhausted"] = True
            return False
        s["attempts"] += 1
        s["reserved_output_tokens"] += limit.max_output_tokens
        s["usage"].append(
            {"input_tokens": None, "output_tokens": None, "cost_usd": None}
        )
        return True

    def record_usage(self, seat, usage):
        self.seats[seat]["usage"][-1] = deepcopy(usage)

    def snapshot(self):
        def summarize(rows):
            usage = [u for r in rows for u in r["usage"]]
            result = {
                k: sum(r[k] for r in rows)
                for k in ("attempts", "reserved_output_tokens", "fallbacks")
            }
            result["budget_exhausted"] = any(r["budget_exhausted"] for r in rows)
            for key in ("input_tokens", "output_tokens", "cost_usd"):
                known = [u[key] for u in usage if u[key] is not None]
                result[key] = sum(known) if usage and len(known) == len(usage) else None
                result["known_" + key] = sum(known) if known else None
                result["missing_" + key + "_attempts"] = len(usage) - len(known)
            return result

        return {
            "total": summarize(self.seats),
            "by_player": {str(i): summarize([s]) for i, s in enumerate(self.seats)},
        }


class LLMPlayer:
    def __init__(
        self,
        table_id,
        seat,
        config,
        budget,
        seed=42,
        transport=None,
        trace_sink=None,
        exporter=None,
    ):
        self.table_id, self.seat, self.config = table_id, seat, deepcopy(config)
        self.budget, self.limits = budget, budget.limits
        self.transport, self.trace_sink, self.exporter = transport, trace_sink, exporter
        self.rng = random.Random(seed)
        self.memory, self.events = [], []
        self.discarded_turns = self.discarded_events = self.last_event = 0
        self.last_trace = None

    def observe_public(self, events):
        fresh = [e for e in public_events(events) if int(e["id"][1:]) > self.last_event]
        if fresh:
            self.last_event = max(int(e["id"][1:]) for e in fresh)
            combined = self.events + fresh
            self.discarded_events += max(0, len(combined) - 64)
            self.events = combined[-64:]

    def accepted(self, obs, decision):
        if obs["player"] != self.seat or obs["table_id"] != self.table_id:
            raise ValueError("Private memory scope mismatch")
        self.memory.append(
            {
                "hand": obs["hand"],
                "state_version": obs["version"],
                "hole": obs["hole"],
                "board": obs["board"],
                "action": decision["action"],
                "summary": decision["summary"],
            }
        )
        keep = self.limits.memory_turns
        self.discarded_turns += max(0, len(self.memory) - keep)
        self.memory = self.memory[-keep:] if keep else []

    def context(self, obs):
        context = {
            "observation": deepcopy(obs),
            "memory": {
                "turns": deepcopy(self.memory),
                "public_events": deepcopy(self.events),
                "discarded_turns": self.discarded_turns,
                "discarded_events": self.discarded_events,
            },
            "max_message_chars": self.limits.max_message_chars,
        }
        # Drop oldest private memory/public evidence first. Never silently truncate
        # the current legal menu, current hand or acting player's cards.
        while len(json.dumps(context, ensure_ascii=True)) > self.limits.max_input_chars:
            memory = context["memory"]
            if memory["turns"]:
                memory["turns"].pop(0)
                memory["discarded_turns"] += 1
            elif memory["public_events"]:
                memory["public_events"].pop(0)
                memory["discarded_events"] += 1
            elif context["observation"]["chat"]["messages"]:
                context["observation"]["chat"]["messages"].pop(0)
                context["observation"]["chat"]["truncated"] = True
            else:
                raise ValueError("input_limit")
        return context

    def schema(self, obs):
        properties = {
            "action": {"type": "string", "enum": [a["key"] for a in obs["legal"]]},
            "summary": {"type": "string"},
            "uncertainty": {"type": "string"},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
            "public_message": {"type": ["string", "null"]},
        }
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }

    async def request(self, obs, context):
        payload = {
            "model": self.config["model"],
            "temperature": self.config["temperature"],
            "max_tokens": self.limits.max_output_tokens,
            "provider": {"require_parameters": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "player_decision",
                    "strict": True,
                    "schema": self.schema(obs),
                },
            },
            "messages": [
                {"role": "system", "content": instruction(self.config["chat_enabled"])},
                {"role": "user", "content": json.dumps(context, ensure_ascii=True)},
            ],
        }
        with current_trace.get().span(
            "model_call",
            "llm",
            {
                "messages": payload["messages"],
                "max_tokens": payload["max_tokens"],
                "temperature": payload["temperature"],
            },
            self.config["model"],
        ) as span:
            async with asyncio.timeout(self.limits.deadline_seconds):
                async with httpx.AsyncClient(
                    timeout=self.limits.deadline_seconds, transport=self.transport
                ) as client:
                    async with client.stream(
                        "POST",
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": "Bearer "
                            + os.getenv("OPENROUTER_API_KEY", ""),
                            "X-Title": "What's Their Range?",
                        },
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        content = bytearray()
                        async for chunk in response.aiter_bytes():
                            content.extend(chunk)
                            if len(content) > 131072:
                                raise ValueError("response_limit")
                        raw = json.loads(content)
            if not isinstance(raw, dict):
                raise ValueError("provider_shape")
            usage = usage_from_provider(raw.get("usage"))
            self.budget.record_usage(self.seat, usage)
            span["usage"] = usage
            value = json.loads(raw["choices"][0]["message"]["content"])
            # Do not put invalid/spoofed response fields in trace outputs.
            if not isinstance(value, dict):
                raise ValueError("decision_shape")
        with current_trace.get().span(
            "validate_response", "tool", {"legal": obs["legal"]}
        ) as span:
            allowed = {
                "action",
                "summary",
                "uncertainty",
                "evidence_ids",
                "public_message",
            }
            if set(value) - allowed or value.get("action") not in [
                a["key"] for a in obs["legal"]
            ]:
                raise ValueError("invalid_action_or_attribution")
            for key in ("summary", "uncertainty"):
                if (
                    not isinstance(value.get(key), str)
                    or not 1 <= len(value[key]) <= 1500
                ):
                    raise ValueError("invalid_summary")
            available = {e["id"] for e in context["observation"]["history"]}
            available.update(
                e["id"]
                for p in context["observation"]["opponents"]
                for e in p["recent_actions"]
            )
            available.update(e["id"] for e in context["memory"]["public_events"])
            available.update(
                e["id"] for e in context["observation"]["chat"]["messages"]
            )
            ids = value.get("evidence_ids")
            if (
                not isinstance(ids, list)
                or len(ids) > 10
                or any(not isinstance(i, str) or i not in available for i in ids)
            ):
                raise ValueError("invalid_evidence")
            message = value.get("public_message")
            if message is not None and (
                not self.config["chat_enabled"]
                or not isinstance(message, str)
                or not 1 <= len(message) <= self.limits.max_message_chars
                or any(ord(c) < 32 for c in message)
            ):
                raise ValueError("invalid_chat")
            span["outputs"] = {"valid": True, **value}
        return {**value, "usage": usage}

    async def decide(self, observation):
        obs = private_observation(observation)
        if obs["player"] != self.seat or obs["table_id"] != self.table_id:
            raise ValueError("Player observation scope mismatch")
        if not self.config["chat_enabled"]:
            obs["chat"]["messages"] = []
        trace = Trace(obs, self.trace_sink)
        trace.record["metadata"].update(
            prompt_version=PROMPT_VERSION,
            prompt_sha256=prompt_hash(self.config["chat_enabled"]),
            harness_version=HARNESS_VERSION,
        )
        token, start = current_trace.set(trace), time.perf_counter()
        try:
            with trace.span(
                "player_turn", inputs={"observation": obs}, root=True
            ) as root:
                reason, value, attempted = None, None, False
                try:
                    context = self.context(obs)
                    if not self.budget.reserve(self.seat):
                        reason = "Provider budget exhausted"
                    else:
                        attempted = True
                        value = await self.request(obs, context)
                except (TimeoutError, httpx.TimeoutException):
                    reason = "Model deadline exceeded"
                except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
                    reason = "Model request or response validation failed"
                if reason:
                    self.budget.seats[self.seat]["fallbacks"] += 1
                    with trace.span("fallback", inputs={"reason": reason}) as span:
                        metrics = assess({"observation": obs})["metrics"]
                        value = {
                            "action": baseline(obs, metrics, self.rng),
                            "summary": "Operational heuristic fallback.",
                            "uncertainty": "No accepted model decision for this turn.",
                            "evidence_ids": [],
                            "public_message": None,
                            "usage": deepcopy(self.budget.seats[self.seat]["usage"][-1])
                            if attempted
                            else {
                                "input_tokens": None,
                                "output_tokens": None,
                                "cost_usd": None,
                            },
                        }
                        span["outputs"] = {
                            "action": value["action"],
                            "source": "heuristic",
                        }
                decision = {
                    **value,
                    "source": "heuristic" if reason else "openrouter",
                    "fallback": reason,
                    "model": self.config["model"],
                    "player": self.seat,
                    "state_version": obs["version"],
                    "chat_sequence": obs["chat"]["last_sequence"],
                    "observation": obs,
                    "metrics": {},
                    "evidence": obs["opponents"],
                    "calls": self.budget.seats[self.seat]["attempts"],
                    "prompt_version": PROMPT_VERSION,
                    "prompt_sha256": prompt_hash(self.config["chat_enabled"]),
                    "harness_version": HARNESS_VERSION,
                    "trace_id": trace.record["trace_id"],
                    "langsmith_url": None,
                }
                root["outputs"] = {
                    k: decision[k]
                    for k in ("action", "source", "fallback", "public_message")
                }
            return {
                **decision,
                "latency_ms": round((time.perf_counter() - start) * 1000, 3),
            }
        finally:
            current_trace.reset(token)
            self.last_trace = trace.record
            if self.exporter:
                self.exporter.submit(trace.record)

    def close(self):
        self.memory.clear()
        self.events.clear()
