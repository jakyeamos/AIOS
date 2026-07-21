from __future__ import annotations

from datetime import datetime
from pathlib import Path

from services.business.config import load_sources_config
from services.business.connectors.discord import DiscordConnector
from services.business.connectors.gmail import GmailConnector
from services.business.connectors.manual import ManualConnector
from services.business.connectors.x import XConnector
from services.business.models import IngestRunSummary
from services.business.normalize import MANUAL_SOURCE_SUFFIXES
from services.business.paths import MANUAL_INBOX
from services.business.store import persist_records


def get_connector(source_name: str, config: dict | None = None):
    config = config or load_sources_config()
    if source_name == "manual":
        manual = config.get("manual", {})
        inbox = manual.get("inbox_path")
        inbox_path = Path(inbox).expanduser() if inbox else MANUAL_INBOX
        if not inbox_path.is_absolute():
            from services.business.paths import AIOS_ROOT

            inbox_path = (AIOS_ROOT / inbox_path).resolve()
        return ManualConnector(inbox_path=inbox_path)
    if source_name == "gmail":
        return GmailConnector(config.get("gmail", {}))
    if source_name == "discord":
        return DiscordConnector(config.get("discord", {}))
    if source_name == "x":
        return XConnector(config.get("x", {}))
    raise ValueError(f"Unknown source: {source_name}")


def sync_source(
    conn,
    source_name: str,
    *,
    since: datetime | None = None,
    move_manual_inbox: bool = True,
) -> IngestRunSummary:
    config = load_sources_config()
    source_cfg = config.get(source_name, {})
    if source_name != "manual" and not source_cfg.get("enabled", False):
        return IngestRunSummary(
            run_id="skipped",
            source_type=source_name,
            status="skipped",
            records_fetched=0,
            records_new=0,
            records_duplicate=0,
            errors=[f"{source_name} is disabled in config"],
        )

    connector = get_connector(source_name, config)
    if not connector.is_configured():
        return IngestRunSummary(
            run_id="skipped",
            source_type=source_name,
            status="skipped",
            records_fetched=0,
            records_new=0,
            records_duplicate=0,
            errors=[f"{source_name} is not configured"],
        )

    records = connector.sync(since)
    summary = persist_records(
        conn,
        records,
        source_type=source_name,
        config_snapshot=source_cfg,
    )

    if source_name == "manual" and move_manual_inbox and isinstance(connector, ManualConnector):
        for path in sorted(connector.inbox_path.iterdir()):
            if path.is_file() and path.suffix.lower() in MANUAL_SOURCE_SUFFIXES:
                connector.mark_processed(path)

    return summary


def sync_all(conn, *, since: datetime | None = None) -> list[IngestRunSummary]:
    config = load_sources_config()
    summaries: list[IngestRunSummary] = []
    for source_name in ("manual", "gmail", "discord", "x"):
        source_cfg = config.get(source_name, {})
        if source_name == "manual" or source_cfg.get("enabled", False):
            try:
                summaries.append(sync_source(conn, source_name, since=since))
            except NotImplementedError as exc:
                summaries.append(
                    IngestRunSummary(
                        run_id="skipped",
                        source_type=source_name,
                        status="skipped",
                        records_fetched=0,
                        records_new=0,
                        records_duplicate=0,
                        errors=[str(exc)],
                    )
                )
    return summaries
