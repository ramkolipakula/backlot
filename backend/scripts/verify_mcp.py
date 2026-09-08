"""
Verify BACKLOT telemetry is queryable via official Grafana MCP.
Tests: list_datasources, query_prometheus, query_loki_logs
"""
import asyncio
import os
import json
import shutil
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

load_dotenv()

GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_TOKEN = os.getenv("GRAFANA_SERVICE_ACCOUNT_TOKEN")

# Incident window: now-29min to now  (current timestamps used by seeder)
# We give a slight buffer: query now-35min to now+2min
now = datetime.now(timezone.utc)
START_RFC3339 = (now - timedelta(minutes=35)).strftime("%Y-%m-%dT%H:%M:%SZ")
END_RFC3339 = (now + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_mcp_cmd():
    """Same fallback logic as backlot_agent.py resolve_mcp_grafana_command."""
    env_cmd = os.getenv("MCP_GRAFANA_COMMAND")
    if env_cmd:
        parts = env_cmd.split()
        return parts[0], parts[1:]

    for fn in (shutil.which("mcp-grafana"), ):
        if fn:
            return fn, []

    uvx = shutil.which("uvx")
    if uvx:
        return uvx, ["mcp-grafana"]

    import pathlib
    fallback_dirs = []
    userprofile = os.environ.get("USERPROFILE", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    if userprofile:
        local_py = pathlib.Path(userprofile) / "AppData" / "Local" / "Python"
        if local_py.is_dir():
            for sub in sorted(local_py.iterdir(), reverse=True):
                fallback_dirs.append(sub / "Scripts")
        fallback_dirs.append(pathlib.Path(userprofile) / "AppData" / "Local" / "uv" / "bin")
        fallback_dirs.append(pathlib.Path(userprofile) / ".local" / "bin")
    if localappdata:
        fallback_dirs.append(pathlib.Path(localappdata) / "uv" / "bin")

    for d in fallback_dirs:
        for name in ("uvx.exe", "uvx", "mcp-grafana.exe", "mcp-grafana"):
            candidate = d / name
            if candidate.is_file():
                if "mcp-grafana" in name:
                    return str(candidate), []
                return str(candidate), ["mcp-grafana"]

    raise RuntimeError("mcp-grafana / uvx not found on PATH or known fallback dirs")


async def run_mcp_verification():
    cmd, args = resolve_mcp_cmd()
    params = StdioServerParameters(
        command=cmd, args=args,
        env={
            "GRAFANA_URL": GRAFANA_URL,
            "GRAFANA_SERVICE_ACCOUNT_TOKEN": GRAFANA_TOKEN,
            "PATH": os.getenv("PATH", ""),
        },
    )

    print(f"MCP command: {cmd} {' '.join(args)}")
    print(f"Query window: {START_RFC3339} -> {END_RFC3339}")
    print()

    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            print("✓ MCP initialize: OK")

            # --- 1. list_datasources ---
            result = await asyncio.wait_for(
                session.call_tool("list_datasources", arguments={"limit": 50}),
                timeout=15.0
            )
            raw = "".join(c.text for c in result.content if hasattr(c, "text"))
            parsed = json.loads(raw)
            ds_list = parsed.get("datasources", parsed) if isinstance(parsed, dict) else parsed
            print(f"✓ list_datasources: found {len(ds_list)} datasources")

            prom_uid = None
            loki_uid = None
            for ds in ds_list:
                print(f"  {ds.get('name')} ({ds.get('type')}) uid={ds.get('uid')}")
                # Prefer the main grafanacloud-prom datasource (not billing/usage)
                if ds.get("type") == "prometheus":
                    uid = ds.get("uid", "")
                    name = ds.get("name", "")
                    # Skip billing/usage datasource
                    if "usage" not in uid and "usage" not in name and "billing" not in uid:
                        prom_uid = uid
                if ds.get("type") == "loki":
                    uid = ds.get("uid", "")
                    name = ds.get("name", "")
                    # Prefer exact match for the official cloud logs datasource
                    if uid == "grafanacloud-logs" or "pinkgoat2043-logs" in name:
                        loki_uid = uid
                    # Fallback if the official one hasn't been found yet
                    elif not loki_uid and ("alert" not in uid and "usage" not in uid
                            and "insight" not in uid and "alert" not in name):
                        loki_uid = uid

            if not prom_uid:
                print("ERROR: No Prometheus datasource found!")
                return
            if not loki_uid:
                print("WARNING: No Loki datasource found (may be expected if write token missing)")

            print()
            print(f"Using Prometheus uid: {prom_uid}")
            print(f"Using Loki uid: {loki_uid}")
            print()

            # --- 2. query_prometheus: packet drop ratio ---
            print(f"Querying: backlot_tracking_packet_drop_ratio [{START_RFC3339} → {END_RFC3339}]")
            result2 = await asyncio.wait_for(
                session.call_tool("query_prometheus", arguments={
                    "datasourceUid": prom_uid,
                    "expr": 'backlot_tracking_packet_drop_ratio{job="backlot_synthetic"}',
                    "queryType": "range",
                    "startTime": START_RFC3339,
                    "endTime": END_RFC3339,
                    "stepSeconds": 60,
                }),
                timeout=20.0
            )
            raw2 = "".join(c.text for c in result2.content if hasattr(c, "text"))
            try:
                p2 = json.loads(raw2)
            except Exception:
                p2 = {"raw": raw2}
            data2 = p2.get("data", p2)
            if isinstance(data2, list) and len(data2) > 0:
                print(f"✓ PROMETHEUS PASS: backlot_tracking_packet_drop_ratio returned {len(data2)} series")
                for series in data2[:2]:
                    vals = series.get("values", series.get("datapoints", []))
                    print(f"  Labels: {series.get('metric', series.get('labels', {}))}")
                    print(f"  Sample count: {len(vals)}")
                    if vals:
                        print(f"  First sample: {vals[0]}")
                        print(f"  Last sample: {vals[-1]}")
            else:
                print(f"✗ PROMETHEUS EMPTY: {str(p2)[:400]}")

            print()

            # --- 3. query_prometheus: DIT buffer ---
            print(f"Querying: backlot_dit_ingest_buffer_percent [{START_RFC3339} → {END_RFC3339}]")
            result3 = await asyncio.wait_for(
                session.call_tool("query_prometheus", arguments={
                    "datasourceUid": prom_uid,
                    "expr": 'backlot_dit_ingest_buffer_percent{job="backlot_synthetic"}',
                    "queryType": "range",
                    "startTime": START_RFC3339,
                    "endTime": END_RFC3339,
                    "stepSeconds": 60,
                }),
                timeout=20.0
            )
            raw3 = "".join(c.text for c in result3.content if hasattr(c, "text"))
            try:
                p3 = json.loads(raw3)
            except Exception:
                p3 = {"raw": raw3}
            data3 = p3.get("data", p3)
            if isinstance(data3, list) and len(data3) > 0:
                print(f"✓ PROMETHEUS PASS: backlot_dit_ingest_buffer_percent returned {len(data3)} series")
                for series in data3[:2]:
                    vals = series.get("values", series.get("datapoints", []))
                    print(f"  Sample count: {len(vals)}")
                    if vals:
                        print(f"  First sample: {vals[0]}")
                        print(f"  Last sample: {vals[-1]}")
            else:
                print(f"✗ PROMETHEUS EMPTY: {str(p3)[:400]}")

            print()

            # --- 4. query_loki_logs (may fail if no write token) ---
            if loki_uid:
                print(f"Querying: Loki logs [{START_RFC3339} → {END_RFC3339}]")
                result4 = await asyncio.wait_for(
                    session.call_tool("query_loki_logs", arguments={
                        "datasourceUid": loki_uid,
                        "logql": '{job="backlot_synthetic"}',
                        "startRfc3339": START_RFC3339,
                        "endRfc3339": END_RFC3339,
                        "limit": 50,
                    }),
                    timeout=20.0
                )
                raw4 = "".join(c.text for c in result4.content if hasattr(c, "text"))
                try:
                    p4 = json.loads(raw4)
                except Exception:
                    p4 = {"raw": raw4}
                data4 = p4.get("data", p4)
                if isinstance(data4, list) and len(data4) > 0:
                    print(f"✓ LOKI PASS: returned {len(data4)} log entries")
                    for entry in data4[:3]:
                        print(f"  {entry}")
                else:
                    print(f"✗ LOKI EMPTY (expected if no write token): {str(p4)[:300]}")
            else:
                print("Skipping Loki query (no datasource found)")


if __name__ == "__main__":
    asyncio.run(run_mcp_verification())
