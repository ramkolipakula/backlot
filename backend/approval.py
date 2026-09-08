"""
BACKLOT Phase 4 — Approval & Grafana Annotation Writeback
Architecture: React → FastAPI → MCP client → Official Grafana MCP → Grafana Cloud
"""
import os
import asyncio
import logging
import shutil
from datetime import datetime, timezone
from typing import Optional

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

from backend.engine.cpm import ProductionCPMEngine
from backend.models.cpm import InterventionResult, InvestigationResult

logger = logging.getLogger("backlot.approval")

# ── MCP command resolution (same pattern as backlot_agent.py) ─────────────── #

def resolve_mcp_grafana_command():
    """Resolve the mcp-grafana launcher command."""
    env_cmd = os.getenv("MCP_GRAFANA_COMMAND")
    if env_cmd:
        parts = env_cmd.split()
        return parts[0], parts[1:]
    mcp_grafana = shutil.which("mcp-grafana")
    if mcp_grafana:
        return mcp_grafana, []
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
                else:
                    return str(candidate), ["mcp-grafana"]

    return None, []


# ── Scenario name display map ──────────────────────────────────────────────── #

SCENARIO_DISPLAY_NAMES = {
    "intervention-a": "A — Hardware Swap",
    "intervention-b": "B — Band B + Buffer Bypass",
    "intervention-c": "C — Abandon / Reschedule",
}

CAUSAL_PATH = (
    "IR Strobe Interference → Optical Tracking Packet Loss → "
    "UE5 Frustum Tracking Jitter → Camera Recording Halt → "
    "DIT Ingest Buffer Saturation → Stage 4 Production Halt"
)


# ── Annotation payload builder ─────────────────────────────────────────────── #

def build_annotation_payload(
    incident: InvestigationResult,
    scenario: InterventionResult,
    actor_hard_out_utc: str,
    decision_ts_ms: int,
) -> dict:
    """
    Builds the create_annotation MCP tool arguments from authoritative backend data.
    Timestamp: epoch milliseconds (integer) as required by discovered MCP schema.
    Tags: concise, alphanumeric.
    Text: structured plain-text block for Grafana readability.
    actor_hard_out_utc: sourced from baseline.actor_hard_out_utc (InterventionResult
    does not carry this field — it is on FinancialModel).
    """
    display_name = SCENARIO_DISPLAY_NAMES.get(scenario.id, scenario.id)
    wrap_display = _fmt_utc_time(scenario.projected_wrap_utc)
    hard_out_display = _fmt_utc_time(actor_hard_out_utc)

    if scenario.actor_hard_out_breached:
        hard_out_status = "BREACHED"
    else:
        delta_min = round(
            (
                _parse_utc(actor_hard_out_utc)
                - _parse_utc(scenario.projected_wrap_utc)
            ).total_seconds()
            / 60
        )
        hard_out_status = f"PRESERVED · {delta_min} MIN BUFFER"

    text = f"""BACKLOT INCIDENT DECISION

Incident: Stage 4 — Scene 24: The Citadel Infiltration

Decision: {display_name}

Status: HUMAN APPROVED

Projected Wrap: {wrap_display} UTC

Actor Hard-Out: {hard_out_display} UTC — {hard_out_status}

Remaining Delay: {scenario.remaining_delay_minutes} min

Total Exposure: ${scenario.total_usd:,}

Savings vs Baseline: ${scenario.net_savings_usd:,}

Causal Path: {CAUSAL_PATH}

Evidence Source: Grafana Prometheus + Loki via official Grafana MCP"""

    # Tag derivation — sanitised alphanumeric with hyphens
    scenario_letter = scenario.id.replace("intervention-", "")
    tags = [
        "backlot",
        "incident",
        "stage-4",
        "scene-24",
        "human-approved",
        f"intervention-{scenario_letter}",
    ]

    return {
        "text": text,
        "tags": tags,
        "time": decision_ts_ms,
    }


# ── Time helpers ───────────────────────────────────────────────────────────── #

def _parse_utc(utc_str: str) -> datetime:
    """Parse a UTC ISO string (Z suffix) to an aware datetime."""
    return datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _fmt_utc_time(utc_str: str) -> str:
    """Format '2026-09-08T18:20:00Z' → '18:20'."""
    dt = _parse_utc(utc_str)
    return dt.strftime("%H:%M")


# ── Core approval & writeback service ─────────────────────────────────────── #

class ApprovalService:
    """
    Handles the full human-approval → Grafana annotation writeback flow.
    One instance per approval request; not reused.
    """

    def __init__(self):
        self.grafana_url = os.getenv("GRAFANA_URL")
        self.grafana_token = os.getenv("GRAFANA_SERVICE_ACCOUNT_TOKEN")

    def _get_mcp_env(self) -> dict:
        return {
            "GRAFANA_URL": self.grafana_url,
            "GRAFANA_SERVICE_ACCOUNT_TOKEN": self.grafana_token,
            "PATH": os.getenv("PATH", ""),
            "USERPROFILE": os.getenv("USERPROFILE", ""),
            "LOCALAPPDATA": os.getenv("LOCALAPPDATA", ""),
            "SYSTEMROOT": os.getenv("SYSTEMROOT", ""),
        }

    async def execute_approval(self, scenario_id: str) -> dict:
        """
        Full approval flow:
          1. Validate credentials
          2. Load authoritative scenario from deterministic engine
          3. Build annotation payload
          4. Invoke create_annotation via official Grafana MCP
          5. Verify with get_annotations
          6. Return structured result
        """
        # ── 1. Credential guard ───────────────────────────────────────────── #
        if not self.grafana_url or not self.grafana_token:
            raise ValueError("Grafana credentials not configured.")

        # ── 2. Load deterministic scenario (source of truth) ─────────────── #
        engine = ProductionCPMEngine()
        incident = engine.process_incident()

        valid_ids = [i.id for i in incident.interventions]
        if scenario_id not in valid_ids:
            raise ValueError(
                f"Unknown scenario_id '{scenario_id}'. Valid: {valid_ids}"
            )

        scenario = next(i for i in incident.interventions if i.id == scenario_id)

        # ── 3. Build annotation payload ───────────────────────────────────── #
        now_utc = datetime.strptime(incident.incident_time_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        decision_ts_ms = int(now_utc.timestamp() * 1000)
        # actor_hard_out_utc lives on FinancialModel (baseline), not InterventionResult
        actor_hard_out_utc = incident.baseline.actor_hard_out_utc
        annotation_args = build_annotation_payload(
            incident, scenario, actor_hard_out_utc, decision_ts_ms
        )

        # ── 4 & 5. MCP writeback + verification ──────────────────────────── #
        cmd, args = resolve_mcp_grafana_command()
        if not cmd:
            raise RuntimeError("mcp-grafana executable not found.")

        mcp_server_params = StdioServerParameters(
            command=cmd,
            args=args,
            env=self._get_mcp_env(),
        )

        logger.info(
            "APPROVAL_REQUESTED scenario_id=%s incident_id=%s",
            scenario_id,
            incident.incident_id,
        )

        annotation_id = None
        verification_result = None
        mcp_raw_response = None

        async with stdio_client(mcp_server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # ── 4. Write annotation ───────────────────────────────────── #
                logger.info(
                    "GRAFANA_ANNOTATION_WRITE_STARTED tool=create_annotation scenario=%s",
                    scenario_id,
                )
                try:
                    write_result = await asyncio.wait_for(
                        session.call_tool("create_annotation", arguments=annotation_args),
                        timeout=15.0,
                    )
                    # Extract text response
                    raw_text = ""
                    for content_item in write_result.content:
                        if hasattr(content_item, "text"):
                            raw_text += content_item.text

                    mcp_raw_response = raw_text

                    # Parse annotation ID from response
                    import json
                    try:
                        parsed = json.loads(raw_text)
                        annotation_id = parsed.get("id") or parsed.get("annotationId")
                        if not annotation_id and isinstance(parsed, dict):
                            # Some Grafana versions return {"message": "Annotation added", "id": 42}
                            annotation_id = parsed.get("id")
                    except (json.JSONDecodeError, TypeError):
                        # Try to extract id from plain text
                        import re
                        m = re.search(r'"id"\s*:\s*(\d+)', raw_text)
                        if m:
                            annotation_id = int(m.group(1))

                    logger.info(
                        "GRAFANA_ANNOTATION_WRITE_SUCCEEDED tool=create_annotation "
                        "annotation_id=%s scenario=%s",
                        annotation_id,
                        scenario_id,
                    )

                except asyncio.TimeoutError:
                    logger.error(
                        "GRAFANA_ANNOTATION_WRITE_FAILED reason=timeout scenario=%s",
                        scenario_id,
                    )
                    raise RuntimeError("Grafana MCP annotation write timed out.")
                except Exception as exc:
                    logger.error(
                        "GRAFANA_ANNOTATION_WRITE_FAILED reason=%s scenario=%s",
                        exc,
                        scenario_id,
                    )
                    raise RuntimeError(f"Grafana MCP annotation write failed: {exc}")

                # ── 5. Verify (read back) ─────────────────────────────────── #
                try:
                    verify_args: dict = {
                        "tags": ["backlot", "human-approved"],
                        "limit": 5,
                    }
                    verify_result = await asyncio.wait_for(
                        session.call_tool("get_annotations", arguments=verify_args),
                        timeout=10.0,
                    )
                    verify_text = ""
                    for content_item in verify_result.content:
                        if hasattr(content_item, "text"):
                            verify_text += content_item.text

                    try:
                        verify_parsed = json.loads(verify_text)
                        verification_result = {
                            "verified": True,
                            "annotations_found": len(verify_parsed) if isinstance(verify_parsed, list) else 1,
                        }
                    except (json.JSONDecodeError, TypeError):
                        verification_result = {
                            "verified": bool(verify_text),
                            "raw": verify_text[:200],
                        }

                except Exception as verify_exc:
                    logger.warning("Annotation verification step failed: %s", verify_exc)
                    verification_result = {"verified": False, "error": str(verify_exc)}

        # ── 6. Return structured result ───────────────────────────────────── #
        display_name = SCENARIO_DISPLAY_NAMES.get(scenario_id, scenario_id)
        return {
            "success": True,
            "annotation_id": annotation_id,
            "scenario_id": scenario_id,
            "scenario_name": display_name,
            "projected_wrap_utc": scenario.projected_wrap_utc,
            "actor_hard_out_utc": actor_hard_out_utc,
            "actor_hard_out_breached": scenario.actor_hard_out_breached,
            "remaining_delay_minutes": scenario.remaining_delay_minutes,
            "total_usd": scenario.total_usd,
            "net_savings_usd": scenario.net_savings_usd,
            "decision_timestamp_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mcp_tool": "create_annotation",
            "verification": verification_result,
        }
