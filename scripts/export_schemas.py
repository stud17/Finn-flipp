"""Eksporter oppdatert JSON Schema fra de faktiske Pydantic-modellene."""

import json
from pathlib import Path

from finnflip.models import Candidate, Config, Feedback, Reference, Trade
from finnflip.sources import RightsManifest

root = Path(__file__).resolve().parent.parent / "docs/schemas"
root.mkdir(parents=True, exist_ok=True)
for model in (Candidate, Reference, Config, Feedback, Trade, RightsManifest):
    (root / f"{model.__name__}.json").write_text(
        json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
print(f"Eksporterte seks skjemaer til {root}")
