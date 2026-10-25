"""Stable neutral interactive baseline; no personality or prompt rotation."""

from .models import TournamentConfig


def neutral_table(model=""):
    return TournamentConfig(
        name="LLM table",
        opponents="llm",
        player_count=6,
        hero_seat=0,
        hero_control="human",
        model=model,
        seat_configs=[{"seat": i, "name": f"Player {i + 1}"} for i in range(6)],
    ).model_dump()
