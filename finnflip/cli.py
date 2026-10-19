from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from .models import Feedback, Trade
from .notifications import export_drafts, prepare_outbox, send_outbox
from .service import ROOT, comparison_csv, import_source, load_config, load_demo, run_analysis
from .sources import LocalFileAdapter, bounded_read
from .storage import Store


def main():
    parser = argparse.ArgumentParser(description="FINN-flippemaskin – lokal analyse og offentlige FINN-sider")
    parser.add_argument("--db", type=Path, default=ROOT / "data/finnflip.sqlite")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="Importer syntetiske data, vurder og lag utkast")
    imp = commands.add_parser("import", help="Importer avklarte lokale brukerdata")
    imp.add_argument("kind", choices=["candidates", "references"])
    imp.add_argument("file", type=Path)
    imp.add_argument("--rights-file", type=Path, required=True)
    assess = commands.add_parser("assess", help="Vurder med dagens konfigurasjon")
    assess.add_argument("--at", help="Historisk tidspunkt med tidssone; kun da kjente data")
    commands.add_parser("drafts", help="Opprett og eksporter A-varsler og B-samlerapport")
    commands.add_parser("list", help="Vis siste vurderinger")
    commands.add_parser("send", help="Send ekte utkast dersom SMTP er eksplisitt aktivert")
    scrape = commands.add_parser("scrape", help="Hent nye kandidater fra offentlige FINN-søkesider")
    scrape.add_argument("--source-config", type=Path, default=ROOT / "scrape.json")
    scrape.add_argument(
        "--watch", action="store_true", help="Gjenta innhenting med konfigurert pause; stopp med Ctrl+C"
    )
    morning = commands.add_parser("morning", help="Hent FINN og rapporter bare positive økonomiske anslag")
    morning.add_argument("--source-config", type=Path, default=ROOT / "scrape.json")
    commands.add_parser("ack-morning", help="Kvitter mulighetene som rapporteres fra siste morgenkjøring")
    report = commands.add_parser("report", help="Eksporter sammenligning med enkel baseline")
    report.add_argument("--output", type=Path, default=ROOT / "data/comparison.csv")
    for cmd in ("feedback", "trade"):
        child = commands.add_parser(cmd, help="Registrer tilbakemelding/handel fra lokal JSON")
        child.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        cfg, store = load_config(args.config), Store(args.db)
        if args.command == "demo":
            print(json.dumps(load_demo(store, cfg), indent=2))
        elif args.command == "morning":
            import requests

            from .morning import morning_report, write_report
            from .scraper import load_scrape_config, scrape_once

            options = load_scrape_config(args.source_config)
            try:
                scrape_once(store, cfg, options)
            except requests.RequestException as exc:
                parser.exit(2, f"Morgeninnhenting stoppet: {type(exc).__name__}\n")
            result = morning_report(store, options.detail_refresh_minutes)
            write_report(args.db.parent / "morning-report.json", result)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.command == "ack-morning":
            from .morning import acknowledge_report

            acknowledge_report(args.db.parent)
            print("Rapporterte muligheter er kvittert.")
        elif args.command == "scrape":
            import time

            import requests

            from .scraper import SourceBlocked, load_scrape_config, scrape_once

            options = load_scrape_config(args.source_config)
            while True:
                pause = options.min_interval_seconds
                try:
                    print(
                        json.dumps(scrape_once(store, cfg, options), indent=2, ensure_ascii=False), flush=True
                    )
                except (ValueError, requests.RequestException) as exc:
                    print(
                        f"Innhenting stoppet: {exc if isinstance(exc, ValueError) else type(exc).__name__}",
                        flush=True,
                    )
                    if not args.watch:
                        parser.exit(2)
                    if isinstance(exc, SourceBlocked):
                        pause = max(pause, 3600)
                if not args.watch:
                    break
                try:
                    time.sleep(pause)
                except KeyboardInterrupt:
                    break
        elif args.command == "import":
            print(
                f"Importert {import_source(store, LocalFileAdapter(args.file, args.rights_file), args.kind)} nye revisjoner"
            )
        elif args.command == "assess":
            from datetime import datetime

            at = datetime.fromisoformat(args.at) if args.at else None
            print(f"Lagret {len(run_analysis(store, cfg, at))} vurderinger")
        elif args.command == "drafts":
            print(f"Nye utkast: {prepare_outbox(store, run_analysis(store, cfg), cfg)}")
            export_drafts(store, args.db.parent / "drafts")
        elif args.command == "list":
            for a in store.assessments():
                print(
                    f"{'DEMO ' if a.candidate.demo else ''}{a.candidate_key:28} {a.grade} "
                    f"score={a.score} overskudd={a.economic_profit} | {a.candidate.title}"
                )
        elif args.command == "send":
            print(json.dumps(send_outbox(store, cfg)))
        elif args.command == "report":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(comparison_csv(store), encoding="utf-8-sig")
            print(args.output)
        elif args.command == "feedback":
            store.feedback(Feedback.model_validate_json(bounded_read(args.file)))
            print("Tilbakemelding registrert")
        elif args.command == "trade":
            trade = Trade.model_validate_json(bounded_read(args.file))
            store.save_trade(trade)
            print(json.dumps(trade.result(), default=str, ensure_ascii=False))
    except ValidationError as exc:
        # Do not echo untrusted file contents or credentials in errors.
        errors = [{"field": ".".join(map(str, e["loc"])), "type": e["type"]} for e in exc.errors()]
        parser.exit(2, f"Validering feilet: {errors}\n")
    except KeyboardInterrupt:
        parser.exit(0, "Innhenting stoppet.\n")
    except (ValueError, OSError, PermissionError) as exc:
        parser.exit(2, f"Operasjonen stoppet: {exc}\n")


if __name__ == "__main__":
    main()
