"""Build a source-only GitHub/Codex Cloud handoff using an explicit allowlist."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent
TOP_FILES = (
    ".gitattributes",
    ".gitignore",
    ".python-version",
    "AGENTS.md",
    "START_HER_GITHUB_OG_CODEX_CLOUD.md",
    "README.md",
    "FINN_FlippeMaskin_Prosjektplan_og_Codex_Prompt.md",
    "Start flippemaskin.command",
    "app.py",
    "config.json",
    "scrape.json",
    "pyproject.toml",
    "requirements.lock.txt",
)
SOURCE_DIRS = ("finnflip", "scripts", "tests", "fixtures", "docs")
ALLOWED_SUFFIXES = {".py", ".sh", ".md", ".json", ".csv", ".png"}


def package(output: Path):
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    mail = config["mail"]
    if mail["mode"] != "DRY_RUN" or any(
        mail.get(key) for key in ("owner_address", "from_address", "smtp_host")
    ):
        raise ValueError("Pakken krever DRY_RUN uten personlige e-postinnstillinger i config.json")
    files = [ROOT / name for name in TOP_FILES] + [ROOT / ".streamlit/config.toml"]
    for directory in SOURCE_DIRS:
        files.extend(
            p
            for p in (ROOT / directory).rglob("*")
            if p.is_file()
            and p.suffix in ALLOWED_SUFFIXES
            and not any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(ROOT).parts)
        )
    files = sorted(set(files))
    if any(path.is_symlink() for path in files):
        raise ValueError("Pakken skal ikke inneholde symbolske lenker")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "GitHub source upload and Codex Cloud setup",
        "local_database_included": False,
        "automation_transferred": False,
        "files": [
            {
                "path": p.relative_to(ROOT).as_posix(),
                "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
            for p in files
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, f"Finn-Flippemaskin/{path.relative_to(ROOT).as_posix()}")
        archive.writestr(
            "Finn-Flippemaskin/PAKKEINNHOLD.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        )
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP-kontroll feilet")
    print(f"{output}\n{len(files) + 1} filer · {output.stat().st_size:,} byte")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/Finn-Flippemaskin-GitHub-Codex-Cloud.zip")
    package(parser.parse_args().output)
