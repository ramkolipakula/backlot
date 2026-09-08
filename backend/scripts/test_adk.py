"""
Direct ADK investigation test — verifies C (ADK + real telemetry).
Runs the full BacklotAgentRunner and prints all SSE events.
Does NOT use FastAPI. Directly drives the async generator.
"""
import asyncio
import json
import sys
import os

# Ensure repo root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from backend.agent.backlot_agent import BacklotAgentRunner

QUERY = (
    "Investigate the Stage 4 virtual production incident. "
    "Determine what telemetry evidence is available regarding tracking packet drops, "
    "Unreal frustum tracking jitter, recording state, and DIT ingest buffer pressure. "
    "Use Grafana MCP telemetry only. Report exact returned values and timestamps. "
    "Do not invent missing evidence. Do not calculate financial impact or interventions."
)


async def main():
    print("=" * 70)
    print("BACKLOT ADK Investigation Test")
    print("=" * 70)
    print(f"Query: {QUERY[:80]}...")
    print()

    runner = BacklotAgentRunner()
    tool_calls = 0
    telemetry_received = 0
    events_received = []

    async for sse_event in runner.stream_generator(QUERY):
        raw = sse_event.get("data", "{}")
        try:
            evt = json.loads(raw)
        except Exception:
            evt = {"raw": raw}

        evt_type = evt.get("type", "UNKNOWN")
        events_received.append(evt_type)

        # Print all events
        if evt_type == "TOOL_CALL_STARTED":
            tool_calls += 1
            print(f"  [TOOL #{tool_calls}] {evt.get('tool')} args={json.dumps(evt.get('args', {}))[:120]}")
        elif evt_type == "TELEMETRY_RECEIVED":
            telemetry_received += 1
            evidence = evt.get("evidence", {})
            ev_str = json.dumps(evidence)
            print(f"  [TELEMETRY] tool={evt.get('tool')} data_len={len(ev_str)}")
            # Print first series/entry
            if isinstance(evidence, dict):
                data = evidence.get("data", evidence)
                if isinstance(data, list) and data:
                    first = data[0]
                    vals = first.get("values", first.get("datapoints", []))
                    print(f"    Series labels: {first.get('metric', first.get('labels', {}))}")
                    print(f"    Samples: {len(vals)}")
                    if vals:
                        print(f"    First: {vals[0]}  Last: {vals[-1]}")
        elif evt_type in ("INVESTIGATION_STARTED", "GRAFANA_MCP_CONNECTED",
                          "DATASOURCES_DISCOVERED", "INVESTIGATION_COMPLETE",
                          "INVESTIGATION_INCOMPLETE", "EVALUATING_EVIDENCE"):
            print(f"  [{evt_type}] {evt.get('message', '')[:100]}")
        elif evt_type in ("ERROR", "TOOL_CALL_FAILED"):
            print(f"  [{evt_type}] code={evt.get('code')} msg={evt.get('message', '')[:150]}")
        elif evt_type in ("DISCOVERING_GRAFANA_CAPABILITIES", "QUERYING_TELEMETRY",
                          "TOOL_CALL_SUCCEEDED"):
            print(f"  [{evt_type}] {evt.get('message', '')[:80]}")
        else:
            print(f"  [{evt_type}]")

    print()
    print("=" * 70)
    print("INVESTIGATION SUMMARY")
    print("=" * 70)
    print(f"Events received:      {events_received}")
    print(f"Tool calls made:      {tool_calls} (limit: 5)")
    print(f"Telemetry received:   {telemetry_received}")
    print()

    if tool_calls > 0 and telemetry_received > 0:
        print("ADK + REAL TELEMETRY: PASS")
    elif tool_calls > 0 and telemetry_received == 0:
        print("ADK + REAL TELEMETRY: PARTIAL (tools called but no telemetry received)")
    elif "ERROR" in events_received or "INVESTIGATION_INCOMPLETE" in events_received:
        print("ADK + REAL TELEMETRY: FAIL (errors in event stream)")
    else:
        print("ADK + REAL TELEMETRY: FAIL (no tool calls made)")


if __name__ == "__main__":
    asyncio.run(main())
