import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv

from backend.agent.backlot_agent import BacklotAgentRunner

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="BACKLOT Phase 1")

# NOTE: CORS is permissive for local development only.
# In production, restrict allow_origins to your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DEVELOPMENT ONLY
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/stream")
async def stream(query: str):
    """
    Streams a BACKLOT investigation as Server-Sent Events.
    The investigation path is:
        FastAPI → ADK Runner → Gemini 2.5 Flash → McpToolset → Official Grafana MCP → Grafana Cloud
    """
    runner = BacklotAgentRunner()
    return EventSourceResponse(runner.stream_generator(query))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
