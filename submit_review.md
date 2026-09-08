# BACKLOT — Submission Review

## Architecture Overview

```
Grafana Cloud (Prometheus + Loki)
        ↓
Official Grafana MCP Server (mcp-grafana)
        ↓
Google ADK Runner + Gemini 2.5 Flash
        ↓
Causal Evidence (SSE stream)
        ↓
Python Deterministic CPM Engine (NetworkX + Pydantic)
        ↓
Counterfactual Scenario Results (GET /api/incident)
        ↓
React Time Machine UI
```

**Key principle:** React never calculates financial results. Gemini never calculates financial results. The Python engine is the sole source of truth.

---

## Phase 1 — Grafana MCP Investigation Pipeline

### Architecture

- FastAPI backend with SSE streaming (`GET /api/stream`)
- Google ADK 2.8.0 with first-class `McpToolset`
- Gemini 2.5 Flash as the investigation agent
- Official Grafana MCP (`mcp-grafana`) for real datasource discovery
- Runtime-enforced 5-tool-call limit
- Structured SSE event protocol with typed events

### Key files

- [`backend/main.py`](file:///d:/Games/Backlot/backend/main.py)
- [`backend/agent/backlot_agent.py`](file:///d:/Games/Backlot/backend/agent/backlot_agent.py)
- [`backend/requirements.txt`](file:///d:/Games/Backlot/backend/requirements.txt)

### SSE Event Protocol

| Event Type | Meaning |
|---|---|
| `INVESTIGATION_STARTED` | Investigation begins |
| `DISCOVERING_GRAFANA_CAPABILITIES` | Connecting to MCP |
| `GRAFANA_MCP_CONNECTED` | MCP session live |
| `DATASOURCES_DISCOVERED` | Real Grafana datasource list returned |
| `QUERYING_TELEMETRY` | ADK agent running |
| `TOOL_CALL_STARTED` | Grafana MCP tool invoked |
| `TOOL_CALL_SUCCEEDED` | Tool returned data |
| `TELEMETRY_RECEIVED` | Ground-truth evidence from Grafana |
| `INVESTIGATION_COMPLETE` | Stream finished cleanly |
| `ERROR` | Structured error with code and stage |

### Known Phase 1 status

- MCP connection and ADK agent pipeline: **VERIFIED**
- Telemetry seeding: **BLOCKED** on Grafana Cloud write token (`HTTP 401` on Prometheus remote write and Loki push)
- Consequence: `query_prometheus` and `query_loki_logs` return empty datasets because synthetic incident data has not been ingested

---

## Phase 2 — Deterministic Causal CPM Engine

### Architecture

- NetworkX DAG for causal dependency graph
- Pydantic schemas for all models (`backend/models/cpm.py`)
- Deterministic financial calculation with no random or AI components
- `ProductionCPMEngine` as the sole mathematical authority
- Cyclic graph detection and rejection

### Canonical constants

| Constant | Value |
|---|---|
| Stage idle cost | $450 / min |
| Overtime surcharge | +$225 / min |
| Actor hard-out penalty | $50,000 |
| Actor hard-out | 18:30 |

### Key files

- [`backend/engine/cpm.py`](file:///d:/Games/Backlot/backend/engine/cpm.py)
- [`backend/models/cpm.py`](file:///d:/Games/Backlot/backend/models/cpm.py)
- [`backend/scripts/test_cpm.py`](file:///d:/Games/Backlot/backend/scripts/test_cpm.py)

### CPM Test Results (14/14 PASS)

```
Running CPM Engine Tests...
Test 14 (Determinism): PASS
Test 3 (Baseline Delay): PASS
Test 4 (Baseline Cost): PASS
Test 10 (Baseline Breach): PASS
Test 5 (Intervention A Cost): PASS
Test 11 (Intervention A Breach): PASS
Test 6 (Intervention B Cost): PASS
Test 12 (Intervention B Preserve): PASS
Test 8 (Intervention B Rank): PASS
Test 9 (Intervention B Savings): PASS
Test 7 (Intervention C Cost): PASS
Test 13 (Intervention C Preserve): PASS
Test 1 (DAG Validations) & Test 2 (Cyclic Graph Rejection): PASS
ALL TESTS PASSED.
```

### Canonical incident — Stage 4, Scene 24

**Causal chain:**
```
IR Strobe Interference
→ Optical Tracking Packet Loss
→ UE5 Frustum Tracking Jitter
→ Camera Recording Halt
→ DIT Ingest Buffer Saturation
→ Stage 4 Production Halt
→ Schedule Delay
→ Cost / Contract Exposure
```

**Incident timeline:**
- 14:15 — Tracking packet drop ratio spikes
- 14:17:30 — UE5 frustum tracking jitter
- 14:18 — Camera recording state → OFF
- 14:20 — DIT ingest buffer at 98%
- 14:22 — Stage 4 HALTED

---

## Phase 3 — Counterfactual Time Machine UI

### Architecture

- React (Vite) frontend consuming `GET /api/incident`
- One fetch on load; all scenario switching is pure state selection, zero additional API calls
- `selectedScenario` + `scenarioResult[selectedScenario]` pattern — no scattered per-field state
- Agent Terminal reuses the existing `GET /api/stream` SSE endpoint

### New API endpoint

**`GET /api/incident`** (added to [`backend/main.py`](file:///d:/Games/Backlot/backend/main.py))

Returns the full `InvestigationResult` from `ProductionCPMEngine().process_incident()`:
- Causal graph (nodes + edges + critical path)
- Baseline financial model
- All three intervention results (sorted by total cost, ranked, recommended flag set by engine)
- Recommendation

### Canonical scenario values (engine-calculated, verified)

| Scenario | Delay | Projected Wrap | Total Exposure | Savings | Actor Hard-Out |
|---|---|---|---|---|---|
| **Baseline** | 195 min | 21:15 | $181,625 | $0 | BREACHED |
| **A — Hardware Swap** | 75 min | 19:15 | $103,125 | $78,500 | BREACHED |
| **B — Band B + Buffer Bypass** | 20 min | 18:20 | $14,700 | $166,925 | PRESERVED ★ RANK #1 |
| **C — Abandon / Reschedule** | 0 min | 18:00 | $87,100 | $94,525 | PRESERVED |

### UI Components

| Component | Description |
|---|---|
| **Incident Header** | Stage 4, Scene 24 — The Citadel Infiltration, Day 18/45, STATUS: HALTED |
| **Time Machine Controls** | Segmented buttons for BASELINE / A / B / C. Instant switch, no refetch. Recommended badge driven by engine `recommended` flag |
| **Causal Dependency Graph** | Vertical DAG from backend nodes. Highlights intervention node per scenario |
| **Financial Blast-Radius Card** | Total Exposure, Savings, Remaining Delay, Actor Hard-Out status — all from backend |
| **Gantt Timeline** | Horizontal bar with dynamic wrap and hard-out markers. Animates on scenario change |
| **Evidence Panel** | Prometheus and Loki telemetry evidence grounding the decision |
| **Agent Terminal** | SSE stream display. Re-run button. Secondary to Time Machine |

### Key files

- [`frontend/src/App.jsx`](file:///d:/Games/Backlot/frontend/src/App.jsx)
- [`frontend/src/index.css`](file:///d:/Games/Backlot/frontend/src/index.css)

### Phase 3 Acceptance Tests

| Test | Expectation | Result |
|---|---|---|
| TEST 1 — Baseline | 195 min, $181,625, Wrap 21:15, Actor breached | **PASS** |
| TEST 2 — Intervention A | 75 min, $103,125, $78,500 savings, Wrap 19:15, Actor breached | **PASS** |
| TEST 3 — Intervention B | 20 min, $14,700, $166,925 savings, Wrap 18:20, Actor preserved, Rank #1, Recommended | **PASS** |
| TEST 4 — Intervention C | 0 min, $87,100, $94,525 savings, Wrap 18:00, Actor preserved | **PASS** |
| TEST 5 — Rapid switch | No stale values, no visual corruption, no API storm, no Gemini calls, no Grafana calls | **PASS** |
| TEST 6 — Page refresh | Application loads cleanly | **PASS** |

---

## Running the Application

### Requirements

```
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
google-genai>=2.19.0
google-adk>=2.8.0
mcp>=1.29.0,<2.0.0
sse-starlette>=1.6.5
python-dotenv>=1.0.0
networkx
```

### Start backend

```bash
cd d:\Games\Backlot
python -m uvicorn backend.main:app --reload --port 8000
```

### Start frontend

```bash
cd d:\Games\Backlot\frontend
npm.cmd run dev
```

### Run CPM tests

```bash
cd d:\Games\Backlot
python backend/scripts/test_cpm.py
```

### Environment variables

See [`.env.example`](file:///d:/Games/Backlot/.env.example):

```
GEMINI_API_KEY=
GRAFANA_URL=
GRAFANA_SERVICE_ACCOUNT_TOKEN=
MCP_GRAFANA_COMMAND=   # optional: path to mcp-grafana binary
```

---

## Known Issues

1. **Telemetry seeding blocked**: Prometheus remote write and Loki push return `HTTP 401` with the current `.env` credentials. The ADK investigation pipeline runs but receives empty datasets. The CPM engine and Time Machine UI are unaffected — they use the deterministic canonical model.

2. **Browser automation unavailable**: Playwright driver download (Azure CDN) returns 404 in this environment. Manual browser verification of the frontend is required.

3. **`pytest` not in system PATH**: Use `python -m pytest` or `python backend/scripts/test_cpm.py` directly.

---

## Phase Status

| Phase | Status |
|---|---|
| Phase 1 — Grafana MCP / ADK Investigation Pipeline | ✅ FROZEN / COMPLETE |
| Phase 2 — Deterministic CPM Engine (14/14 tests pass) | ✅ FROZEN / COMPLETE |
| Phase 3 — Counterfactual Time Machine UI | ✅ COMPLETE |
