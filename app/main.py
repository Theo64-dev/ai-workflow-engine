from fastapi import FastAPI, HTTPException

import app.workflows.summarization

from app.engine import engine, EngineError
from app.model import (
    GraphCreateRequest,
    GraphCreateResponse,
    GraphRunRequest,
    GraphRunResponse,
    RunStateResponse,
)

app = FastAPI(
    title="Minimal Workflow Engine",
    description="A small LangGraph-style workflow engine built with FastAPI.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Workflow engine is running"}


@app.post("/graph/create", response_model=GraphCreateResponse)
def create_graph(payload: GraphCreateRequest):
    """
    Define a new workflow graph.

    Validates that all node names exist in the registry and stores
    the graph in the in-memory engine.
    """
    try:
        graph = engine.create_graph(payload)
        return GraphCreateResponse(graph_id=graph.id)
    except EngineError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # generic fallback
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/graph/run", response_model=GraphRunResponse)
def run_graph(request: GraphRunRequest):
    """
    Run a previously created graph synchronously with an initial state.

    Returns:
    - run_id
    - final_state (after all nodes have executed)
    - execution_log (list of node names in order)
    - status ("completed" or "failed")
    """
    try:
        result = engine.run_graph(request.graph_id, request.initial_state)
        return result
    except EngineError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/graph/state/{run_id}", response_model=RunStateResponse)
def get_run_state(run_id: str):
    """
    Get the current state of a workflow run.

    In this basic implementation, runs are synchronous and in-memory,
    so this usually returns the final state immediately.
    """
    try:
        return engine.get_run_state_response(run_id)
    except EngineError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
