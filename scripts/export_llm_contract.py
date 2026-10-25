"""Run with PYTHONPATH=apps/api and the API virtual environment."""

import json
from pathlib import Path

from wtr.llmbench.manifest import Manifest
from wtr.models import Control, HeroAction, TournamentConfig
from wtr.presets import neutral_table

root = Path(__file__).resolve().parents[1]
for name, model in (
    ("llm-table-config", TournamentConfig),
    ("hero-action", HeroAction),
    ("table-control", Control),
    ("llm-benchmark", Manifest),
):
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **model.model_json_schema(),
    }
    (root / "contracts" / f"{name}-v1.schema.json").write_text(
        json.dumps(schema, indent=2) + "\n"
    )
(root / "contracts/examples/llm-six-seat-neutral.json").write_text(
    json.dumps(neutral_table(), indent=2) + "\n"
)
