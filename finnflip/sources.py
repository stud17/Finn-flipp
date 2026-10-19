from __future__ import annotations

import csv
import hashlib
import io
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from pydantic import Field

from .models import Candidate, Model, Reference, utcnow

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10000


class RightsManifest(Model):
    approved_by: str = Field(min_length=2, max_length=100)
    approved_at: datetime
    basis: str = Field(min_length=20, max_length=2000)
    purposes: list[str]
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_file: str
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class SourceAdapter(ABC):
    @abstractmethod
    def load(self, kind: str) -> tuple[list, dict]:
        """Return validated observations and auditable source provenance."""


def bounded_read(path: Path) -> bytes:
    with path.open("rb") as file:
        content = file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError("Filen overskrider 5 MiB")
    return content


def parse_rows(content: bytes, suffix: str, kind: str) -> list:
    if kind not in {"candidates", "references"}:
        raise ValueError("Ukjent importtype")
    if len(content) > MAX_BYTES:
        raise ValueError("Filen overskrider 5 MiB")
    text = content.decode("utf-8-sig")
    if suffix.lower() == ".json":
        rows = json.loads(text)
    elif suffix.lower() == ".csv":
        csv.field_size_limit(MAX_BYTES)
        rows = list(csv.DictReader(io.StringIO(text)))
        for row in rows:
            for key in list(row):
                if row[key] == "":
                    del row[key]
                elif key in {"product", "costs", "risk_flags"}:
                    row[key] = json.loads(row[key])
    else:
        raise ValueError("Bruk JSON eller CSV")
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError("Forventet en liste med høyst 10 000 objekter")
    model = Candidate if kind == "candidates" else Reference
    return [model.model_validate(row) for row in rows]


class LocalFileAdapter(SourceAdapter):
    def __init__(self, path: Path, rights_file: Path):
        self.path, self.rights_file = path, rights_file

    def load(self, kind: str):
        content = bounded_read(self.path)
        manifest = RightsManifest.model_validate_json(bounded_read(self.rights_file))
        if manifest.approved_at.tzinfo is None or manifest.approved_at > utcnow():
            raise ValueError("Rettighetsvurdering må ha et gyldig tidspunkt med tidssone")
        if not {"analysis", "storage", "drafts"}.issubset(manifest.purposes):
            raise ValueError("Rettighetsgrunnlaget må dekke analyse, lagring og utkast")
        if hashlib.sha256(content).hexdigest() != manifest.input_sha256:
            raise ValueError("Rettighetsvurderingen gjelder en annen datafil")
        evidence = (self.rights_file.parent / manifest.evidence_file).resolve()
        proof = bounded_read(evidence)
        if len(proof) < 20 or hashlib.sha256(proof).hexdigest() != manifest.evidence_sha256:
            raise ValueError("Dokumentert rettighetsgrunnlag mangler eller er endret")
        rows = parse_rows(content, self.path.suffix, kind)
        if any(row.demo for row in rows):
            raise ValueError("Bruk demokilden for syntetiske observasjoner")
        return rows, manifest.model_dump(mode="json")


class DemoAdapter(SourceAdapter):
    def __init__(self, root: Path):
        self.root = root

    def load(self, kind: str):
        path = self.root / f"{kind}.json"
        content = bounded_read(path)
        rows = parse_rows(content, ".json", kind)
        if not all(row.demo for row in rows):
            raise ValueError("Demokilden inneholder umerkede rader")
        return rows, {
            "type": "SYNTHETIC_DEMO",
            "sha256": hashlib.sha256(content).hexdigest(),
            "warning": "Oppdiktede data. Ingen dokumentasjon på markedsmuligheten.",
        }


class LicensedFeedAdapter(SourceAdapter):
    def __init__(self, rights_file: Path | None = None, source_config: dict | None = None):
        self.rights_file, self.source_config = rights_file, source_config

    def load(self, kind: str):
        if not self.rights_file or not self.source_config:
            raise PermissionError(
                "Live-feed deaktivert: dokumentert tilgangsavtale og kildekonfigurasjon mangler"
            )
        raise NotImplementedError("Live-feed er ikke implementert. Avtalen må gjennomgås før integrasjon.")
