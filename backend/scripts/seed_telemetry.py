"""
BACKLOT Telemetry Seeder — Phase 1
======================================================
Seeds synthetic incident telemetry into Grafana Cloud.

TIMESTAMP DECISION (documented):
    Grafana Cloud Mimir rejects historical timestamps older than its
    out-of-order ingestion window (typically ~1 hour).  The original
    incident timeline was 2026-09-07T14:00–14:29 UTC, but those
    timestamps are days in the past and cannot be ingested.

    This seeder therefore writes metrics using CURRENT wall-clock time
    so that they land within the Mimir ingest window.  The shape of the
    incident timeline is preserved (30-minute window, 5 metrics,
    incident events at t+15/+17.5/+18/+20/+22 minutes), but the
    absolute timestamps are anchored to `now - 29 min … now`.

    All subsequent MCP queries use RFC3339 timestamps derived from the
    actual times written, which are printed at the end of this script.
    Do NOT query 2026-09-07T14:xx when using this seeder.

LOKI STATUS:
    The LOKI_PASSWORD env var is a READ-ONLY hosted-logs token
    (token name contains 'hl-read'). Loki write requires a separate
    logs:write scoped token which the user must create in Grafana Cloud
    console:  https://grafana.com/orgs/<org>/access-policies
    Set LOKI_PASSWORD to a token with logs:write scope before seeding.
"""
import os
import json
import requests
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("backlot.seeder")

PROMETHEUS_URL = os.getenv("PROMETHEUS_REMOTE_WRITE_URL")
PROMETHEUS_USER = os.getenv("PROMETHEUS_USERNAME")
PROMETHEUS_PASS = os.getenv("PROMETHEUS_PASSWORD")

LOKI_URL = os.getenv("LOKI_PUSH_URL")
LOKI_USER = os.getenv("LOKI_USERNAME")
LOKI_PASS = os.getenv("LOKI_PASSWORD")


def seed_metrics():
    if not (PROMETHEUS_URL and PROMETHEUS_USER and PROMETHEUS_PASS):
        log.error("Missing Prometheus configuration in .env")
        return None

    from prometheus_remote_writer import RemoteWriter

    # Anchor the incident to NOW so Mimir accepts the timestamps.
    # The incident window is t+0 to t+29 minutes.
    now = datetime.now(timezone.utc)
    base_time = now - timedelta(minutes=29)   # oldest sample is ~29 min ago

    log.info("Seeding Prometheus metrics ...")
    log.info(f"  Incident window: {base_time.isoformat()} → {now.isoformat()}")
    log.info(f"  Prometheus URL: {PROMETHEUS_URL}")

    labels = {
        "production": "citadel_infiltration",
        "scene": "scene_24",
        "stage": "stage_4",
        "system": "virtual_production",
        "job": "backlot_synthetic",
    }

    metrics_data = []
    for minute_offset in range(30):
        dt = base_time + timedelta(minutes=minute_offset)
        ts_ms = int(dt.timestamp() * 1000)

        # 1. Packet drop ratio — spikes at offset +15
        val_packet = 0.01 if minute_offset < 15 else (0.184 if minute_offset == 15 else 0.02)
        metrics_data.append({
            "metric": {**labels, "__name__": "backlot_tracking_packet_drop_ratio"},
            "timestamps": [ts_ms], "values": [val_packet],
        })

        # 2. Tracking latency — rises sharply at +15
        val_latency = 5.0 if minute_offset < 15 else 45.5
        metrics_data.append({
            "metric": {**labels, "__name__": "backlot_tracking_latency_ms"},
            "timestamps": [ts_ms], "values": [val_latency],
        })

        # 3. Camera recording state — drops to 0 at +18
        val_rec = 1.0 if minute_offset < 18 else 0.0
        metrics_data.append({
            "metric": {**labels, "__name__": "backlot_camera_recording_state"},
            "timestamps": [ts_ms], "values": [val_rec],
        })

        # 4. DIT ingest buffer — rises after +18, reaches 98 at +20
        if minute_offset < 18:
            val_dit = 45.0
        elif minute_offset == 18:
            val_dit = 60.0
        elif minute_offset == 19:
            val_dit = 85.0
        else:
            val_dit = 98.0
        metrics_data.append({
            "metric": {**labels, "__name__": "backlot_dit_ingest_buffer_percent"},
            "timestamps": [ts_ms], "values": [val_dit],
        })

        # 5. Stage halted — becomes 1 at +22
        val_halt = 0.0 if minute_offset < 22 else 1.0
        metrics_data.append({
            "metric": {**labels, "__name__": "backlot_stage_halted"},
            "timestamps": [ts_ms], "values": [val_halt],
        })

    # Also add disk write latency
    for minute_offset in range(30):
        dt = base_time + timedelta(minutes=minute_offset)
        ts_ms = int(dt.timestamp() * 1000)
        val_disk = 2.0 if minute_offset < 18 else 120.0
        metrics_data.append({
            "metric": {**labels, "__name__": "backlot_disk_write_latency_ms"},
            "timestamps": [ts_ms], "values": [val_disk],
        })

    writer = RemoteWriter(
        url=PROMETHEUS_URL,
        auth={"username": PROMETHEUS_USER, "password": PROMETHEUS_PASS},
    )

    try:
        res = writer.send(metrics_data)
        log.info(f"SUCCESS: series_sent={res.series_sent} samples_sent={res.samples_sent} "
                 f"status={res.last_response.status_code if res.last_response else 'N/A'}")
        return base_time, now
    except Exception as exc:
        log.error(f"FAILED: {exc}")
        return None


def seed_logs(base_time=None):
    if not (LOKI_URL and LOKI_USER and LOKI_PASS):
        log.error("Missing Loki configuration in .env")
        return False

    if base_time is None:
        now = datetime.now(timezone.utc)
        base_time = now - timedelta(minutes=29)

    log.info("Seeding Loki logs ...")
    log.info(f"  Base time: {base_time.isoformat()}")
    log.info(f"  Loki URL: {LOKI_URL}")

    base_labels = {
        "production": "citadel_infiltration",
        "scene": "scene_24",
        "stage": "stage_4",
        "job": "backlot_synthetic",
    }

    events = [
        (0,    "info",  "stage",    "Stage 4 initialization complete. Ready for Scene 24."),
        (5,    "info",  "unreal",   "Unreal Engine sync stabilized at 60fps. Tracking latency 5ms."),
        (10,   "info",  "camera",   "Camera recording state transition to ON."),
        (15,   "warn",  "tracking", "OptiTrack optical packet loss warning exceeded threshold."),
        (17.5, "error", "unreal",   "Frustum tracking jitter of 14.2ms detected. Sync lost."),
        (18,   "info",  "camera",   "Camera recording state transition to OFF."),
        (20,   "warn",  "dit",      "DIT ingest buffer warning: 98% capacity reached!"),
        (22,   "fatal", "stage",    "Stage officially HALTED due to cascading sync and buffer failures."),
    ]

    streams = []
    for offset_mins, lvl, comp, msg in events:
        dt = base_time + timedelta(minutes=offset_mins)
        ts_nano = str(int(dt.timestamp() * 1e9))
        streams.append({
            "stream": {**base_labels, "level": lvl, "component": comp},
            "values": [[ts_nano, msg]],
        })

    payload = {"streams": streams}

    try:
        resp = requests.post(
            LOKI_URL,
            json=payload,
            auth=(LOKI_USER, LOKI_PASS),
            timeout=15,
        )
        if resp.status_code == 204:
            log.info("SUCCESS: Loki logs pushed.")
            return True
        elif resp.status_code == 401:
            body = resp.json() if resp.text else {}
            err = body.get("error", resp.text)
            if "scope" in err.lower():
                log.error(
                    "BLOCKED: Loki token is READ-ONLY (scope: logs:read only). "
                    "Create a logs:write token at https://grafana.com/orgs/<org>/access-policies "
                    "and set it as LOKI_PASSWORD in .env"
                )
            else:
                log.error(f"Loki auth error: {err}")
        else:
            log.error(f"Loki push failed: HTTP {resp.status_code} — {resp.text[:300]}")
    except Exception as exc:
        log.error(f"Loki push exception: {exc}")
    return False


if __name__ == "__main__":
    print("=" * 60)
    print("BACKLOT Telemetry Seeder")
    print("=" * 60)

    result = seed_metrics()
    if result:
        base_time, end_time = result
        print()
        print("PROMETHEUS SEED COMPLETE")
        print(f"  Query window start : {base_time.isoformat()}")
        print(f"  Query window end   : {end_time.isoformat()}")
        print(f"  Use these RFC3339 timestamps for MCP queries.")
        print(f"  DO NOT query 2026-09-07T14:xx — those timestamps are historical.")
    else:
        print("PROMETHEUS SEED FAILED")

    print()
    loki_ok = seed_logs(base_time=result[0] if result else None)
    if not loki_ok:
        print()
        print("LOKI SEED BLOCKED")
        print("  Action required: create a logs:write access policy token in Grafana Cloud")
        print("  https://grafana.com/orgs/<org>/access-policies")
        print("  Update LOKI_PASSWORD in .env with the new token")

    print()
    print("Done.")
