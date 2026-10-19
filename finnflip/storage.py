from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .models import Assessment, Candidate, Feedback, Reference, Trade, fingerprint, utcnow

SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO metadata VALUES ('schema_version', '1');
CREATE TABLE IF NOT EXISTS observations (
 revision INTEGER PRIMARY KEY, kind TEXT NOT NULL, stable_key TEXT NOT NULL,
 digest TEXT NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL,
 UNIQUE(kind, stable_key, digest));
CREATE INDEX IF NOT EXISTS obs_lookup ON observations(kind, stable_key, recorded_at);
CREATE TABLE IF NOT EXISTS assessments (
 id INTEGER PRIMARY KEY, candidate_key TEXT NOT NULL, evaluated_at TEXT NOT NULL,
 payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS feedback (
 id INTEGER PRIMARY KEY, candidate_key TEXT NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS trades (
 candidate_key TEXT PRIMARY KEY, updated_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS trade_history (
 id INTEGER PRIMARY KEY, candidate_key TEXT NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS imports (
 id INTEGER PRIMARY KEY, recorded_at TEXT NOT NULL, kind TEXT NOT NULL, provenance TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outbox (
 id INTEGER PRIMARY KEY, dedup_key TEXT UNIQUE NOT NULL, category TEXT NOT NULL,
 created_at TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'draft',
 subject TEXT NOT NULL, text_body TEXT NOT NULL, html_body TEXT NOT NULL,
 assessments TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, error TEXT);
CREATE TABLE IF NOT EXISTS alert_events (
 id INTEGER PRIMARY KEY, entity_key TEXT NOT NULL, candidate_key TEXT NOT NULL,
 created_at TEXT NOT NULL, outbox_id INTEGER NOT NULL, price TEXT NOT NULL,
 score TEXT NOT NULL, grade TEXT NOT NULL,
 FOREIGN KEY(outbox_id) REFERENCES outbox(id));
CREATE TABLE IF NOT EXISTS scrape_runs (
 id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, state TEXT NOT NULL,
 report TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS live_items (
 candidate_key TEXT PRIMARY KEY, seen_at TEXT NOT NULL, detail_checked_at TEXT,
 search_name TEXT NOT NULL, notes TEXT NOT NULL, last_error TEXT, parser_version TEXT);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)
            if "parser_version" not in {row[1] for row in db.execute("PRAGMA table_info(live_items)")}:
                db.execute("ALTER TABLE live_items ADD COLUMN parser_version TEXT")
            db.execute("UPDATE metadata SET value='2' WHERE key='schema_version'")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def import_rows(self, kind: str, rows: list, provenance: dict, at: datetime | None = None) -> int:
        at = (at or utcnow()).astimezone(timezone.utc)
        count = 0
        with self.connect() as db:
            for row in rows:
                key = f"{row.source}:{row.id}"
                previous = db.execute(
                    "SELECT payload FROM observations WHERE kind=? AND stable_key=? "
                    "ORDER BY revision DESC LIMIT 1",
                    (kind, key),
                ).fetchone()
                digest = fingerprint(row)
                if previous and fingerprint(json.loads(previous["payload"])) == digest:
                    continue
                # Include the revision number so reverting to an earlier price is also history.
                history_digest = fingerprint(
                    [
                        digest,
                        db.execute(
                            "SELECT COUNT(*) FROM observations WHERE kind=? AND stable_key=?", (kind, key)
                        ).fetchone()[0],
                    ]
                )
                db.execute(
                    "INSERT INTO observations(kind,stable_key,digest,recorded_at,payload) VALUES(?,?,?,?,?)",
                    (kind, key, history_digest, at.isoformat(), row.model_dump_json()),
                )
                count += 1
            db.execute(
                "INSERT INTO imports(recorded_at,kind,provenance) VALUES(?,?,?)",
                (at.isoformat(), kind, json.dumps(provenance, ensure_ascii=False)),
            )
        return count

    def observations(self, kind: str, at: datetime | None = None) -> list:
        at = (at or utcnow()).astimezone(timezone.utc)
        with self.connect() as db:
            rows = db.execute(
                "SELECT o.payload,o.recorded_at FROM observations o JOIN "
                "(SELECT stable_key,MAX(revision) revision FROM observations "
                "WHERE kind=? AND recorded_at<=? GROUP BY stable_key) latest "
                "ON o.revision=latest.revision",
                (kind, at.isoformat()),
            ).fetchall()
        model = Candidate if kind == "candidates" else Reference
        result = []
        for row in rows:
            obj = model.model_validate_json(row["payload"])
            if isinstance(obj, Reference):
                obj.known_at = max(obj.known_at, datetime.fromisoformat(row["recorded_at"]))
            result.append(obj)
        return result

    def save_assessments(self, assessments: list[Assessment]):
        with self.connect() as db:
            db.executemany(
                "INSERT INTO assessments(candidate_key,evaluated_at,payload) VALUES(?,?,?)",
                [(a.candidate_key, a.evaluated_at.isoformat(), a.model_dump_json()) for a in assessments],
            )

    def assessments(self) -> list[Assessment]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT a.payload FROM assessments a JOIN "
                "(SELECT candidate_key,MAX(id) id FROM assessments GROUP BY candidate_key) latest "
                "ON a.id=latest.id"
            ).fetchall()
        return sorted(
            [Assessment.model_validate_json(r[0]) for r in rows],
            key=lambda a: (a.score is not None, a.score or 0),
            reverse=True,
        )

    def history(self, candidate_key: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT revision,recorded_at,payload FROM observations WHERE kind='candidates' "
                "AND stable_key=? ORDER BY revision",
                (candidate_key,),
            ).fetchall()
        return [
            {
                "revision": r["revision"],
                "recorded_at": r["recorded_at"],
                "candidate": json.loads(r["payload"]),
            }
            for r in rows
        ]

    def has_candidate(self, key: str, demo: bool):
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM observations WHERE kind='candidates' AND stable_key=? "
                "ORDER BY revision DESC LIMIT 1",
                (key,),
            ).fetchone()
        if not row:
            raise ValueError("Ukjent kandidat")
        if Candidate.model_validate_json(row[0]).demo != demo:
            raise ValueError("Demo-merking må stemme med kandidaten")

    def feedback(self, feedback: Feedback):
        self.has_candidate(feedback.candidate_key, feedback.demo)
        with self.connect() as db:
            db.execute(
                "INSERT INTO feedback(candidate_key,recorded_at,payload) VALUES(?,?,?)",
                (feedback.candidate_key, utcnow().isoformat(), feedback.model_dump_json()),
            )

    def feedback_rows(self) -> list[Feedback]:
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM feedback ORDER BY id").fetchall()
        return [Feedback.model_validate_json(r[0]) for r in rows]

    def save_trade(self, trade: Trade):
        self.has_candidate(trade.candidate_key, trade.demo)
        with self.connect() as db:
            stamp = utcnow().isoformat()
            db.execute(
                "INSERT INTO trades VALUES(?,?,?) ON CONFLICT(candidate_key) DO UPDATE SET "
                "updated_at=excluded.updated_at,payload=excluded.payload",
                (trade.candidate_key, stamp, trade.model_dump_json()),
            )
            db.execute(
                "INSERT INTO trade_history(candidate_key,recorded_at,payload) VALUES(?,?,?)",
                (trade.candidate_key, stamp, trade.model_dump_json()),
            )

    def trades(self) -> list[Trade]:
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM trades").fetchall()
        return [Trade.model_validate_json(row[0]) for row in rows]

    def outbox(self) -> list[dict]:
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM outbox ORDER BY id DESC")]

    def reserve_scrape(self, min_interval_seconds: int, at: datetime | None = None) -> int:
        from datetime import timedelta

        at = at or utcnow()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            last = db.execute("SELECT * FROM scrape_runs ORDER BY id DESC LIMIT 1").fetchone()
            if last:
                pause = max(min_interval_seconds, 3600 if last["state"] == "blocked" else 0)
                remaining = datetime.fromisoformat(last["started_at"]) + timedelta(seconds=pause) - at
                if remaining.total_seconds() > 0 or (
                    last["state"] == "running"
                    and (at - datetime.fromisoformat(last["started_at"])).total_seconds() < 900
                ):
                    raise ValueError(
                        f"Forrige innhenting pågår eller er for nylig. Vent minst {max(1, int(remaining.total_seconds()))} sekunder."
                    )
            return db.execute(
                "INSERT INTO scrape_runs(started_at,state) VALUES(?,'running')", (at.isoformat(),)
            ).lastrowid

    def finish_scrape(self, run_id: int, state: str, report: dict):
        with self.connect() as db:
            db.execute(
                "UPDATE scrape_runs SET finished_at=?,state=?,report=? WHERE id=?",
                (utcnow().isoformat(), state, json.dumps(report, ensure_ascii=False), run_id),
            )

    def latest_scrape(self) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM scrape_runs ORDER BY id DESC LIMIT 1").fetchone()
        return {**dict(row), "report": json.loads(row["report"])} if row else None

    def live_items(self) -> dict[str, dict]:
        with self.connect() as db:
            return {
                row["candidate_key"]: {**dict(row), "notes": json.loads(row["notes"])}
                for row in db.execute("SELECT * FROM live_items")
            }

    def see_live_item(
        self,
        key: str,
        search_name: str,
        notes: list[str],
        checked_at: datetime | None,
        error: str | None = None,
        parser_version: str | None = None,
    ):
        with self.connect() as db:
            db.execute(
                "INSERT INTO live_items(candidate_key,seen_at,detail_checked_at,search_name,notes,last_error,parser_version) VALUES(?,?,?,?,?,?,?) ON CONFLICT(candidate_key) DO UPDATE SET "
                "seen_at=excluded.seen_at,detail_checked_at=COALESCE(excluded.detail_checked_at,live_items.detail_checked_at),"
                "search_name=excluded.search_name,notes=excluded.notes,last_error=excluded.last_error,parser_version=COALESCE(excluded.parser_version,live_items.parser_version)",
                (
                    key,
                    utcnow().isoformat(),
                    checked_at.isoformat() if checked_at else None,
                    search_name,
                    json.dumps(notes, ensure_ascii=False),
                    error,
                    parser_version,
                ),
            )
