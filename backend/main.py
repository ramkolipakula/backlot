import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

from backend.agent.backlot_agent import BacklotAgentRunner
from backend.engine.cpm import ProductionCPMEngine
from backend.approval import ApprovalService

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="BACKLOT Phase 1-4")

# NOTE: CORS is permissive for local development only.
# In production, restrict allow_origins to your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DEVELOPMENT ONLY
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-flight lock: prevents duplicate concurrent annotation writes.
# A simple asyncio.Lock is sufficient for a single-process server.
_approval_lock = asyncio.Lock()
_approval_in_flight: bool = False


# ── Phase 4: Approval request model ──────────────────────────────────────── #

VALID_SCENARIO_IDS = {"intervention-a", "intervention-b", "intervention-c"}


class ApprovalRequest(BaseModel):
    """
    Human approval request.
    Only the scenario identity is accepted from the frontend.
    All financial data is resolved server-side from the deterministic engine.
    """
    scenario_id: str

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, v: str) -> str:
        if v not in VALID_SCENARIO_IDS:
            raise ValueError(
                f"Invalid scenario_id '{v}'. Must be one of: {sorted(VALID_SCENARIO_IDS)}"
            )
        return v


# ── Existing Phase 1–3 endpoints (FROZEN — do not modify) ────────────────── #

@app.get("/api/stream")
async def stream(query: str):
    """
    Streams a BACKLOT investigation as Server-Sent Events.
    The investigation path is:
        FastAPI → ADK Runner → Gemini 2.5 Flash → McpToolset → Official Grafana MCP → Grafana Cloud
    """
    runner = BacklotAgentRunner()
    return EventSourceResponse(runner.stream_generator(query))

@app.get("/api/incident")
async def get_incident():
    """
    Returns the deterministic incident, causal graph, baseline financial model,
    and counterfactual interventions.
    """
    engine = ProductionCPMEngine()
    return engine.process_incident()


# ── Phase 4: Approval endpoint ────────────────────────────────────────────── #

@app.post("/api/approve")
async def approve_intervention(request: ApprovalRequest):
    """
    Human approval → Grafana annotation writeback.

    Flow:
        Validate scenario_id (Pydantic)
        → Load authoritative scenario from deterministic CPM engine
        → Build annotation payload from engine data (no frontend values trusted)
        → Invoke official Grafana MCP create_annotation tool
        → Verify with get_annotations
        → Return structured result

    Security:
        - Grafana credentials never exposed to frontend
        - Frontend submits only scenario_id
        - All financial values sourced from deterministic engine
    """
    global _approval_in_flight

    async with _approval_lock:
        if _approval_in_flight:
            raise HTTPException(
                status_code=409,
                detail="An approval is already in progress. Please wait."
            )
        _approval_in_flight = True

    try:
        service = ApprovalService()
        result = await service.execute_approval(request.scenario_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logging.getLogger("backlot.main").error(
            "Unexpected error in /api/approve: %s", exc, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}")
    finally:
        async with _approval_lock:
            _approval_in_flight = False


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
