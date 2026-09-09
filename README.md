# BACKLOT — AI-Driven Film Production Incident Response System

BACKLOT is a real-time incident response system for virtual film productions. When a stage halt occurs, it uses a live Gemini/ADK investigation over real Grafana telemetry to build evidence, then applies a deterministic CPM (Critical Path Method) engine to rank counterfactual interventions by financial impact. Human approval writes a Grafana annotation into the forensic timeline.

---

## Architecture

```
Frontend (React/Vite)
       |
       | SSE (EventSource)           POST /api/approve
       v                                   |
FastAPI (backend/main.py)                  |
  |                                        |
  | /api/stream                      /api/approve
  v                                        v
BacklotAgentRunner              ApprovalService
  |                                        |
  | Google ADK Runner                      |
  v                                        v
Gemini 3.6 Flash               Grafana MCP (stdio)
  |                             create_annotation
  | McpToolset (stdio)          get_annotations
  v
Official Grafana MCP Server
  - list_datasources
  - query_prometheus
  - query_loki_logs
  |
  v
Grafana Cloud
  - Prometheus (synthetic telemetry)
  - Loki (synthetic logs)

  [After investigation]
  |
  v
ProductionCPMEngine (deterministic)
  - process_incident(evidence=collected_evidence)
  - Causal graph + CPM
  - Financial blast radius
  - Intervention ranking
```

---

## What Is Synthetic vs. Real

| Component | Synthetic / Demo | Real / Live |
|-----------|-----------------|-------------|
| Incident scenario (Stage 4 Scene 24) | ✅ Simulated | — |
| Financial constants ($450/min idle, $225/min OT, $50k penalty) | ✅ Fixed for demo | — |
| Telemetry data (packet_drop_ratio, dit_buffer_percent, logs) | ✅ Seeded by `backend/scripts/seed_telemetry.py` | — |
| Grafana MCP connection | — | ✅ Official mcp-grafana v1.3.0 via stdio |
| Gemini investigation | — | ✅ Live Gemini 3.6 Flash via Google ADK |
| Grafana annotation writeback | — | ✅ Real `create_annotation` call |
| CPM calculation | — | ✅ Deterministic arithmetic, not LLM |

**Canonical verified dollar figures (must never change):**
- Baseline: $181,625
- Intervention A (Hardware Swap): $103,125 (saves $78,500)
- Intervention B (Band Switch + Buffer Bypass): $14,700 (saves $166,925)
- Intervention C (Abandon/Reschedule): $87,100 (saves $94,525)

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (for mcp-grafana)
- Grafana Cloud account with Prometheus and Loki datasources
- Gemini API key

---

## Local Setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd backlot
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_gemini_api_key
GRAFANA_URL=https://your-instance.grafana.net
GRAFANA_SERVICE_ACCOUNT_TOKEN=your_grafana_sa_token
```

### 2. Install mcp-grafana

```bash
uvx mcp-grafana --version   # confirms mcp-grafana is available
# or: pip install mcp-grafana
```

### 3. Backend

```bash
cd backlot
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Seed telemetry (one-time, seeds Grafana with synthetic incident data)

```bash
python backend/scripts/seed_telemetry.py
```

### 5. Frontend

```bash
cd frontend
cp .env.example .env.local   # contains VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Docker

### Backend

```bash
# From repo root
docker build -t backlot-backend .
docker run -p 8000:8000 --env-file .env backlot-backend
```

### Frontend

```bash
# From frontend/
docker build --build-arg VITE_API_URL=http://localhost:8000 -t backlot-frontend .
docker run -p 80:80 backlot-frontend
```

---

## Annotation Timestamp Architecture

The Grafana annotation created on approval is anchored to the **incident time** (`2026-09-08T14:22:00Z`, epoch_ms `1788877320000`), not the wall-clock approval time. This is a deliberate demo-architecture decision: the annotation appears at the correct forensic position on the Grafana timeline, not at a future timestamp.

The `/api/approve` response includes:
- `annotation_timestamp_basis: "incident_time"` — documents this choice explicitly
- `approval_recorded_at` — the actual wall-clock click time, for observability only

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, `/api/stream`, `/api/incident`, `/api/approve` |
| `backend/agent/backlot_agent.py` | ADK + Gemini investigation runner |
| `backend/engine/cpm.py` | Deterministic CPM engine (financial calculations) |
| `backend/models/cpm.py` | Pydantic models (Evidence, RootCause, etc.) |
| `backend/approval.py` | Approval + Grafana annotation writeback |
| `backend/mcp/resolver.py` | Shared mcp-grafana command resolver |
| `frontend/src/App.jsx` | Root component, SSE consumer, state |
| `frontend/src/components/EvidenceTimeline.jsx` | Live evidence from investigation events |
| `frontend/src/components/AgentTerminal.jsx` | Investigation event stream display |
