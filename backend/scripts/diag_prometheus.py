"""Diagnose why Prometheus query failed when datasourceUid is omitted."""
import os, json, asyncio, pathlib
from dotenv import load_dotenv
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession
from datetime import datetime, timezone, timedelta

load_dotenv()

GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_TOKEN = os.getenv("GRAFANA_SERVICE_ACCOUNT_TOKEN")


def resolve_mcp_cmd():
    userprofile = os.environ.get("USERPROFILE", "")
    local_py = pathlib.Path(userprofile) / "AppData" / "Local" / "Python"
    for sub in sorted(local_py.iterdir(), reverse=True):
        uvx = sub / "Scripts" / "uvx.exe"
        if uvx.is_file():
            return str(uvx), ["mcp-grafana"]
    raise RuntimeError("uvx not found")


async def test():
    now = datetime.now(timezone.utc)
    q_start = (now - timedelta(minutes=35)).strftime("%Y-%m-%dT%H:%M:%SZ")
    q_end = (now + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"Query window: {q_start} -> {q_end}")

    cmd, args = resolve_mcp_cmd()
    params = StdioServerParameters(
        command=cmd, args=args,
        env={"GRAFANA_URL": GRAFANA_URL, "GRAFANA_SERVICE_ACCOUNT_TOKEN": GRAFANA_TOKEN, "PATH": os.getenv("PATH", "")},
    )

    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            print("MCP OK")

            # Test 1: WITHOUT datasourceUid
            res1 = await asyncio.wait_for(
                session.call_tool("query_prometheus", arguments={
                    "expr": 'backlot_tracking_packet_drop_ratio{job="backlot_synthetic"}',
                    "queryType": "range",
                    "startTime": q_start,
                    "endTime": q_end,
                    "stepSeconds": 60,
                }),
                timeout=20.0,
            )
            raw1 = "".join(c.text for c in res1.content if hasattr(c, "text"))
            print(f"Test 1 (no uid): {raw1[:300]}")
            print()

            # Test 2: WITH grafanacloud-prom
            res2 = await asyncio.wait_for(
                session.call_tool("query_prometheus", arguments={
                    "datasourceUid": "grafanacloud-prom",
                    "expr": 'backlot_tracking_packet_drop_ratio{job="backlot_synthetic"}',
                    "queryType": "range",
                    "startTime": q_start,
                    "endTime": q_end,
                    "stepSeconds": 60,
                }),
                timeout=20.0,
            )
            raw2 = "".join(c.text for c in res2.content if hasattr(c, "text"))
            p2 = json.loads(raw2)
            data2 = p2.get("data", p2)
            if isinstance(data2, list) and data2:
                series = data2[0]
                vals = series.get("values", [])
                print(f"Test 2 (grafanacloud-prom): {len(data2)} series, {len(vals)} samples")
                print(f"  Labels: {series.get('metric', {})}")
                print(f"  First: {vals[0] if vals else None}")
                print(f"  Last: {vals[-1] if vals else None}")
            else:
                print(f"Test 2 EMPTY: {raw2[:400]}")

            print()

            # Test 3: DIT buffer with grafanacloud-prom
            res3 = await asyncio.wait_for(
                session.call_tool("query_prometheus", arguments={
                    "datasourceUid": "grafanacloud-prom",
                    "expr": 'backlot_dit_ingest_buffer_percent{job="backlot_synthetic"}',
                    "queryType": "range",
                    "startTime": q_start,
                    "endTime": q_end,
                    "stepSeconds": 60,
                }),
                timeout=20.0,
            )
            raw3 = "".join(c.text for c in res3.content if hasattr(c, "text"))
            p3 = json.loads(raw3)
            data3 = p3.get("data", p3)
            if isinstance(data3, list) and data3:
                series3 = data3[0]
                vals3 = series3.get("values", [])
                print(f"Test 3 DIT buffer (grafanacloud-prom): {len(data3)} series, {len(vals3)} samples")
                print(f"  Last (should be 98): {vals3[-1] if vals3 else None}")
            else:
                print(f"Test 3 EMPTY: {raw3[:300]}")

            # Test 4: Loki
            res4 = await asyncio.wait_for(
                session.call_tool("query_loki_logs", arguments={
                    "datasourceUid": "grafanacloud-logs",
                    'logql': '{job="backlot_synthetic"}',
                    "startRfc3339": q_start,
                    "endRfc3339": q_end,
                    "limit": 50,
                }),
                timeout=20.0,
            )
            raw4 = "".join(c.text for c in res4.content if hasattr(c, "text"))
            p4 = json.loads(raw4)
            data4 = p4.get("data", p4)
            print()
            if isinstance(data4, list) and data4:
                print(f"Test 4 Loki: {len(data4)} entries")
                for entry in data4[:3]:
                    print(f"  {entry}")
            else:
                print(f"Test 4 Loki EMPTY (expected without write token): {raw4[:200]}")


if __name__ == "__main__":
    asyncio.run(test())
