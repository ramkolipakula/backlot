"""
SSE end-to-end test — makes a real HTTP request to the FastAPI SSE endpoint
and reads the full event stream. Verifies criterion D.
"""
import requests
import json
import sys

QUERY = (
    "Investigate the Stage 4 virtual production incident. "
    "Determine what telemetry evidence is available regarding tracking packet drops, "
    "DIT ingest buffer pressure. Use Grafana MCP telemetry only. "
    "Report exact returned values. Do not invent missing evidence."
)

URL = f"http://127.0.0.1:8765/api/stream?query={requests.utils.quote(QUERY)}"

print("=" * 70)
print("BACKLOT SSE End-to-End Test")
print("=" * 70)
print(f"URL: {URL[:80]}...")
print()

events_received = []
tool_calls = 0
telemetry_received = 0
errors = 0

try:
    with requests.get(URL, stream=True, timeout=300) as resp:
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"ERROR: {resp.text[:300]}")
            sys.exit(1)

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data:"):
                raw = line[5:].strip()
                try:
                    evt = json.loads(raw)
                except Exception:
                    continue

                evt_type = evt.get("type", "UNKNOWN")
                events_received.append(evt_type)

                if evt_type == "TOOL_CALL_STARTED":
                    tool_calls += 1
                    print(f"  [TOOL #{tool_calls}] {evt.get('tool')} args={json.dumps(evt.get('args', {}))[:100]}")
                elif evt_type == "TELEMETRY_RECEIVED":
                    telemetry_received += 1
                    evidence = evt.get("evidence", {})
                    print(f"  [TELEMETRY] tool={evt.get('tool')} data_size={len(json.dumps(evidence))}")
                    data = evidence.get("data", evidence) if isinstance(evidence, dict) else evidence
                    if isinstance(data, list) and data:
                        series = data[0]
                        vals = series.get("values", [])
                        print(f"    Labels: {series.get('metric', series.get('labels', {}))}")
                        print(f"    Samples: {len(vals)}")
                        if vals:
                            print(f"    First: {vals[0]}  Last: {vals[-1]}")
                elif evt_type in ("ERROR", "TOOL_CALL_FAILED"):
                    errors += 1
                    print(f"  [{evt_type}] {evt.get('code', '')} {evt.get('message', '')[:120]}")
                elif evt_type == "INVESTIGATION_COMPLETE":
                    print(f"  [{evt_type}] {evt.get('message', '')}")
                    break  # Stream complete
                elif evt_type == "INVESTIGATION_INCOMPLETE":
                    print(f"  [{evt_type}] {evt.get('message', '')}")
                    break
                else:
                    msg = evt.get("message", "") or evt.get("datasources", "")
                    print(f"  [{evt_type}] {str(msg)[:80]}")

except requests.exceptions.ConnectionError as e:
    print(f"CONNECTION ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 70)
print("SSE TEST SUMMARY")
print("=" * 70)
print(f"Events received:    {events_received}")
print(f"Tool calls:         {tool_calls}")
print(f"Telemetry received: {telemetry_received}")
print(f"Errors:             {errors}")
print()

required_events = {
    "INVESTIGATION_STARTED", "DISCOVERING_GRAFANA_CAPABILITIES",
    "GRAFANA_MCP_CONNECTED", "DATASOURCES_DISCOVERED", "QUERYING_TELEMETRY",
}
missing = required_events - set(events_received)

if missing:
    print(f"MISSING LIFECYCLE EVENTS: {missing}")

if "INVESTIGATION_COMPLETE" in events_received or "INVESTIGATION_INCOMPLETE" in events_received:
    print("Stream terminated cleanly: YES")
else:
    print("Stream terminated cleanly: NO (no completion event received)")

if tool_calls > 0 and telemetry_received > 0 and not missing:
    print()
    print("SSE END-TO-END: PASS")
elif tool_calls > 0:
    print()
    print("SSE END-TO-END: PARTIAL (tools called, stream functional)")
else:
    print()
    print("SSE END-TO-END: FAIL")
