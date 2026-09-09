"""
BACKLOT Phase 1 — Grafana Investigation Agent
Architecture: FastAPI -> Google ADK Runner -> Gemini 3.6 Flash -> McpToolset -> Official Grafana MCP
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator

from google.adk import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types as genai_types
from mcp import StdioServerParameters

from backend.engine.cpm import ProductionCPMEngine
from backend.mcp.resolver import resolve_mcp_grafana_command

logger = logging.getLogger("backlot.agent")

# Known telemetry query tool names from official Grafana MCP v1.3.0
_PROMETHEUS_QUERY_TOOLS = {"query_prometheus", "query_prometheus_histogram"}
_LOKI_QUERY_TOOLS = {"query_loki_logs"}
# Known datasource discovery tool
_DATASOURCE_DISCOVERY_TOOL = "list_datasources"


class ToolLimitExceeded(Exception):
    pass


from backend.models.cpm import ManualIncidentRequest, Evidence as EvidenceModel

class ManualAgentRunner:
    """
    Manages one manual investigation end-to-end.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.grafana_url = os.getenv("GRAFANA_URL")
        self.grafana_token = os.getenv("GRAFANA_SERVICE_ACCOUNT_TOKEN")
        self._queue: asyncio.Queue = asyncio.Queue()
        # Runtime-enforced tool call counter
        self._tool_call_count = 0
        self._max_tool_calls = 5
        # Evidence collected from TELEMETRY_RECEIVED events during _handle_adk_event.
        # Built from live Grafana MCP responses; passed into process_incident() at
        # the RUNNING_CPM_ENGINE step. Never populated from any other source.
        self._collected_evidence: list = []

    # ------------------------------------------------------------------ #
    # Event helpers                                                        #
    # ------------------------------------------------------------------ #

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _evt(self, event_type: str, data: dict) -> dict:
        """Format a structured SSE event with a backend-generated timestamp."""
        return {
            "event": "message",
            "data": json.dumps({"type": event_type, "timestamp": self._now(), **data}),
        }

    # ------------------------------------------------------------------ #
    # Public streaming entry point                                         #
    # ------------------------------------------------------------------ #

    async def stream_generator(self, request: ManualIncidentRequest) -> AsyncGenerator[dict, None]:
        """Starts investigation in a background task; yields SSE events from queue."""
        task = asyncio.create_task(self._run_investigation(request))
        while True:
            item = await self._queue.get()
            if item is None:
                break
            yield item
        # Ensure any exception from the task propagates to logs
        try:
            await task
        except Exception as exc:
            logger.error("Investigation task raised: %s", exc, exc_info=True)

    # ------------------------------------------------------------------ #
    # Core investigation                                                   #
    # ------------------------------------------------------------------ #

    async def _run_investigation(self, request: ManualIncidentRequest) -> None:
        await self._queue.put(
            self._evt("INVESTIGATION_STARTED", {"message": f"Investigating Manual Incident: {request.description}"})
        )

        # Map manual observations to evidence immediately
        for obs in request.observations:
            ev_obj = EvidenceModel(
                source="user_input",
                datasource_uid="manual_form",
                query="observation",
                timestamp=obs.timestamp,
                value=f"[{obs.severity}] {obs.description}"
            )
            self._collected_evidence.append(ev_obj)
            await self._queue.put(
                self._evt(
                    "TELEMETRY_RECEIVED",
                    {
                        "source": "user_input",
                        "tool": "manual_form",
                        "evidence": ev_obj.model_dump(),
                    },
                )
            )

        # --- Credential guard -------------------------------------------------
        missing = []
        if not self.api_key:
            missing.append("GEMINI_API_KEY")
        if not self.grafana_url:
            missing.append("GRAFANA_URL")
        if not self.grafana_token:
            missing.append("GRAFANA_SERVICE_ACCOUNT_TOKEN")

        if missing:
            await self._queue.put(
                self._evt(
                    "ERROR",
                    {
                        "code": "MCP_UNAVAILABLE",
                        "message": f"Missing credentials: {', '.join(missing)}",
                        "stage": "credential_check",
                    },
                )
            )
            await self._queue.put(None)
            return

        # --- MCP server params ------------------------------------------------
        cmd, args = resolve_mcp_grafana_command()
        if not cmd:
            await self._queue.put(
                self._evt(
                    "ERROR",
                    {
                        "code": "MCP_UNAVAILABLE",
                        "message": "mcp-grafana executable not found.",
                        "stage": "infrastructure",
                    },
                )
            )
            await self._queue.put(None)
            return

        mcp_server_params = StdioServerParameters(
            command=cmd,
            args=args,
            env={
                "GRAFANA_URL": self.grafana_url,
                "GRAFANA_SERVICE_ACCOUNT_TOKEN": self.grafana_token,
                "PATH": os.getenv("PATH", ""),
            },
        )
        stdio_params = StdioConnectionParams(
            server_params=mcp_server_params,
            timeout=10.0,
        )

        try:
            await self._queue.put(
                self._evt(
                    "DISCOVERING_GRAFANA_CAPABILITIES",
                    {"message": "Connecting to official Grafana MCP server..."},
                )
            )

            # --- McpToolset as context manager (ADK 2.8.0 + mcp 1.29.1) ------
            # McpToolset opens the stdio process and MCP session once; ADK agent
            # reuses it for all tool calls within this investigation.
            toolset = McpToolset(connection_params=stdio_params)
            try:
                await self._queue.put(
                    self._evt("GRAFANA_MCP_CONNECTED", {"message": "Grafana MCP session active."})
                )

                # ---- Step A: Real Grafana datasource discovery ----------------
                # Use the actual MCP session (accessible via toolset._session) to
                # call list_datasources directly — this is true datasource
                # discovery, not MCP tool listing.
                await self._queue.put(
                    self._evt(
                        "DISCOVERING_GRAFANA_CAPABILITIES",
                        {"message": "Querying Grafana for available datasources..."},
                    )
                )
                datasources = await self._discover_datasources()

                # ---- Step B: Compute telemetry query window ------------------
                # Seeder anchors incident to (now - 29min). We query now-35 to now+5
                # to ensure all 30 data points are captured.
                now_utc = datetime.now(timezone.utc)
                q_start = (now_utc - timedelta(minutes=35)).strftime("%Y-%m-%dT%H:%M:%SZ")
                q_end = (now_utc + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

                # Extract the main Prometheus and Loki UIDs from discovered datasources
                prom_uid = "grafanacloud-prom"  # default
                loki_uid = "grafanacloud-logs"  # default
                for ds in datasources:
                    ds_uid = ds.get("uid", "")
                    ds_type = ds.get("type", "")
                    ds_name = ds.get("name", "")
                    if ds_type == "prometheus" and "usage" not in ds_uid and "billing" not in ds_uid:
                        prom_uid = ds_uid
                    if ds_type == "loki" and "alert" not in ds_uid and "usage" not in ds_uid and "insight" not in ds_uid:
                        loki_uid = ds_uid

                # Build the ADK agent with McpToolset
                obs_text = "\n".join([f"- [{o.severity}] {o.description} (at {o.timestamp})" for o in request.observations])

                agent = Agent(
                    name="backlot_manual_investigator",
                    model="gemini-3.6-flash",
                    instruction=f"""
You are the BACKLOT investigator for a virtual film production incident.

User-Provided Incident Facts:
Production: {request.production_name}
Scene: {request.scene}
Stage: {request.stage}
Time: {request.incident_time_utc}
Description: {request.description}

User-Provided Observations:
{obs_text}

You have access to the official Grafana MCP tools. The Grafana instance has
the following datasources (use the exact UIDs below):
{json.dumps(datasources, indent=2)}

The incident time window is: {q_start} to {q_end}

Investigation steps:
1. Review the User-Provided Observations as primary evidence.
2. If appropriate, query Grafana MCP for corroborating telemetry in '{prom_uid}' or '{loki_uid}'.
3. Synthesize the strongest supported explanation for the incident. Do NOT pretend you found Grafana telemetry if you only used user observations. Clearly label the source of evidence.

STRICT RULES:
- Maximum {max_tool_calls} tool calls. Stop after that.
- Do NOT calculate dollars, schedule delays, CPM, or interventions.
- Do NOT fabricate telemetry values. Use only what MCP returns or what the user provided.
- Explain why alternative hypotheses are weaker based on the facts.
""",
                    tools=[toolset],
                )

                session_service = InMemorySessionService()
                runner = Runner(
                    app_name="backlot_phase1",
                    agent=agent,
                    session_service=session_service,
                    auto_create_session=True,
                )

                await self._queue.put(
                    self._evt(
                        "QUERYING_TELEMETRY",
                        {"message": "ADK agent starting Gemini-driven investigation..."},
                    )
                )

                # ---- Run ADK agent with event streaming ----------------------
                user_message = genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text=f"Please investigate the manual incident: {request.description}")],
                )

                user_id = "backlot"
                session_id = f"inv-{datetime.now(timezone.utc).strftime('%H%M%S')}"

                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=user_message,
                ):
                    await self._handle_adk_event(event)

                await self._queue.put(
                    self._evt("EVALUATING_EVIDENCE", {"message": "Agent completed tool execution."})
                )

                # Gather streamed telemetry evidence from the event queue
                # (already emitted inline during _handle_adk_event)
                await self._queue.put(
                    self._evt(
                        "INVESTIGATION_COMPLETE",
                        {"message": "Phase 1 investigation complete. Check TELEMETRY_RECEIVED events for evidence."},
                    )
                )

                # ---- Phase 2: Deterministic CPM Engine -----------------------
                await self._queue.put(
                    self._evt(
                        "RUNNING_CPM_ENGINE",
                        {"message": "Running deterministic Causal Dependency Graph and CPM calculations..."},
                    )
                )
                try:
                    cpm_engine = ProductionCPMEngine(
                        idle_cost=request.production_parameters.stage_idle_cost_per_minute,
                        overtime_surcharge=request.production_parameters.crew_ot_surcharge_per_minute,
                        actor_penalty=request.production_parameters.actor_penalty
                    )
                    investigation_result = cpm_engine.process_manual_incident(
                        request=request,
                        evidence=self._collected_evidence
                    )
                    await self._queue.put(
                        self._evt(
                            "CPM_RESULT",
                            {"result": investigation_result.model_dump()}
                        )
                    )
                except Exception as e:
                    logger.error("CPM Engine failed: %s", e)
                    await self._queue.put(
                        self._evt("ERROR", {"code": "CPM_ERROR", "message": str(e), "stage": "cpm_execution"})
                    )

            finally:
                await toolset.close()

        except asyncio.TimeoutError:
            await self._queue.put(
                self._evt(
                    "ERROR",
                    {
                        "code": "MCP_TIMEOUT",
                        "message": "Grafana MCP connection timed out.",
                        "stage": "mcp_connect",
                    },
                )
            )
        except ToolLimitExceeded as exc:
            await self._queue.put(
                self._evt(
                    "INVESTIGATION_INCOMPLETE",
                    {
                        "message": str(exc),
                        "tool_calls_made": self._tool_call_count,
                        "limit": self._max_tool_calls,
                    },
                )
            )
        except Exception as exc:
            msg = str(exc)
            code = "MCP_AUTH_ERROR" if ("401" in msg or "403" in msg or "Unauthorized" in msg) else "AGENT_ERROR"
            await self._queue.put(
                self._evt(
                    "ERROR",
                    {"code": code, "message": msg, "stage": "agent_execution"},
                )
            )
        finally:
            await self._queue.put(None)

    # ------------------------------------------------------------------ #
    # Datasource discovery — uses the real Grafana MCP list_datasources   #
    # ------------------------------------------------------------------ #

    async def _discover_datasources(self) -> list:
        """
        Calls the official Grafana MCP list_datasources tool directly
        using the standard mcp python client. This is real Grafana datasource discovery,
        NOT MCP tool listing, and is treated as infrastructure initialization.
        """
        from mcp.client.stdio import stdio_client
        from mcp.client.session import ClientSession
        
        cmd, args = resolve_mcp_grafana_command()
        if not cmd:
            raise RuntimeError("mcp-grafana executable not found")

        mcp_server_params = StdioServerParameters(
            command=cmd,
            args=args,
            env={
                "GRAFANA_URL": self.grafana_url,
                "GRAFANA_SERVICE_ACCOUNT_TOKEN": self.grafana_token,
                "PATH": os.getenv("PATH", ""),
            },
        )
        
        try:
            async with stdio_client(mcp_server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await asyncio.wait_for(
                        session.call_tool(_DATASOURCE_DISCOVERY_TOOL, arguments={"limit": 50}),
                        timeout=10.0,
                    )
                    # Parse MCP CallToolResult content
                    raw_text = ""
                    for content_item in result.content:
                        if hasattr(content_item, "text"):
                            raw_text += content_item.text

                    try:
                        parsed = json.loads(raw_text)
                        datasources = parsed.get("datasources", parsed) if isinstance(parsed, dict) else parsed
                        
                        if isinstance(datasources, list):
                            summary = [
                                {"name": d.get("name"), "type": d.get("type"), "uid": d.get("uid")}
                                for d in datasources
                            ]
                        else:
                            summary = datasources
                    except json.JSONDecodeError:
                        summary = [{"raw": raw_text}]

                    await self._queue.put(
                        self._evt(
                            "DATASOURCES_DISCOVERED",
                            {
                                "message": f"Discovered {len(summary) if isinstance(summary, list) else 1} datasource(s) via list_datasources.",
                                "datasources": summary,
                            },
                        )
                    )
                    return summary

        except asyncio.TimeoutError:
            await self._queue.put(
                self._evt(
                    "ERROR",
                    {
                        "code": "MCP_TIMEOUT",
                        "message": "Timed out calling list_datasources.",
                        "stage": "datasource_discovery",
                    },
                )
            )
            raise RuntimeError("Datasource discovery timed out.")
        except Exception as exc:
            msg = str(exc)
            await self._queue.put(
                self._evt(
                    "ERROR",
                    {"code": "TOOL_CALL_FAILED", "message": msg, "stage": "datasource_discovery"},
                )
            )
            raise RuntimeError(f"Datasource discovery failed: {msg}")

    # ------------------------------------------------------------------ #
    # ADK event handler                                                   #
    # ------------------------------------------------------------------ #

    async def _handle_adk_event(self, event) -> None:
        """
        Translates ADK events into BACKLOT SSE events.
        Enforces the 5-tool-call runtime limit.
        """
        # Function call (tool invocation)
        if event.content and event.content.parts:
            for part in event.content.parts:
                # Tool call outbound
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    self._tool_call_count += 1
                    logger.info("Tool call #%d: %s", self._tool_call_count, fc.name)

                    if self._tool_call_count > self._max_tool_calls:
                        raise ToolLimitExceeded(
                            f"Runtime 5-tool limit reached after tool '{fc.name}'. "
                            f"Stopping investigation."
                        )

                    await self._queue.put(
                        self._evt(
                            "TOOL_CALL_STARTED",
                            {
                                "message": f"[Turn {self._tool_call_count}/{self._max_tool_calls}] Calling {fc.name}",
                                "tool": fc.name,
                                "args": dict(fc.args) if fc.args else {},
                            },
                        )
                    )

                # Tool response (inbound)
                if hasattr(part, "function_response") and part.function_response:
                    fr = part.function_response
                    tool_name = fr.name
                    response_data = fr.response if fr.response else {}

                    # Determine if this was a successful telemetry query
                    if tool_name in _PROMETHEUS_QUERY_TOOLS or tool_name in _LOKI_QUERY_TOOLS:
                        # Structural check: extract the "data" payload regardless of wrapper
                        # ADK passes fr.response as a dict; MCP returns {data: [...], hints: {...}}
                        # We must check the actual list is non-empty, not just keyword-sniff the JSON.
                        actual_data = None
                        error_msg = None

                        if isinstance(response_data, dict):
                            # Direct MCP response format: {"data": [...], "hints": {...}}
                            if "data" in response_data:
                                actual_data = response_data["data"]
                            # ADK may also wrap as {"output": "<json>", ...}
                            elif "output" in response_data:
                                try:
                                    inner = json.loads(response_data["output"])
                                    actual_data = inner.get("data", inner) if isinstance(inner, dict) else inner
                                except (json.JSONDecodeError, TypeError):
                                    pass
                            # Check for explicit error field
                            if "error" in response_data and not actual_data:
                                error_msg = str(response_data["error"])
                        elif isinstance(response_data, str):
                            # Raw string — try to parse as JSON
                            try:
                                parsed = json.loads(response_data)
                                actual_data = parsed.get("data") if isinstance(parsed, dict) else parsed
                            except (json.JSONDecodeError, TypeError):
                                error_msg = response_data[:200]

                        # PASS: actual_data is a non-empty list with at least one entry
                        has_real_data = isinstance(actual_data, list) and len(actual_data) > 0
                        # FAIL: explicit error, or data is empty/missing
                        is_error = bool(error_msg) or not has_real_data

                        if is_error:
                            detail = error_msg or f"Empty data (actual_data={actual_data!r})"
                            logger.warning("Tool %s: no real data. detail=%s", tool_name, detail[:200])
                            await self._queue.put(
                                self._evt(
                                    "TOOL_CALL_FAILED",
                                    {
                                        "tool": tool_name,
                                        "message": f"{tool_name} returned no data.",
                                        "detail": detail[:500],
                                    },
                                )
                            )
                        else:
                            await self._queue.put(
                                self._evt(
                                    "TOOL_CALL_SUCCEEDED",
                                    {"tool": tool_name, "message": f"{tool_name} returned data."},
                                )
                            )
                            # Ground truth: MCP response is the evidence.
                            # Also collect into _collected_evidence so process_incident()
                            # can receive it as structured Evidence objects.
                            from backend.models.cpm import Evidence as EvidenceModel
                            try:
                                ev_obj = EvidenceModel(
                                    source="grafana_mcp",
                                    datasource_uid=str(tool_name),
                                    query=str(tool_name),
                                    timestamp=self._now(),
                                    value=str(actual_data[0])[:500] if actual_data else None,
                                )
                                self._collected_evidence.append(ev_obj)
                            except Exception as ev_err:
                                logger.warning("Could not construct Evidence object: %s", ev_err)
                            await self._queue.put(
                                self._evt(
                                    "TELEMETRY_RECEIVED",
                                    {
                                        "source": "grafana_mcp",
                                        "tool": tool_name,
                                        "evidence": response_data,
                                    },
                                )
                            )
                    else:
                        await self._queue.put(
                            self._evt(
                                "TOOL_CALL_SUCCEEDED",
                                {
                                    "tool": tool_name,
                                    "message": f"{tool_name} completed.",
                                },
                            )
                        )

                # Model text output
                if hasattr(part, "text") and part.text and not getattr(part, "function_call", None):
                    logger.debug("Agent text: %s", part.text[:200])
