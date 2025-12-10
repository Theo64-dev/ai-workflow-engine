from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


# ---- Core type aliases ----

State = Dict[str, Any]          # Shared state that flows between nodes
NodeName = str                  # String alias for clarity
GraphId = str
RunId = str


# ---- Graph definition models ----

class GraphCreateRequest(BaseModel):
    """
    Payload expected by POST /graph/create.
    Describes the workflow graph the client wants to define.
    """
    name: str = Field(..., description="Human-readable name for the graph")
    entry_node: NodeName = Field(..., description="Name of the starting node")
    nodes: List[NodeName] = Field(..., description="List of node names used in this graph")

    # Linear edges: node -> next node (or null to stop)
    edges: Dict[NodeName, Optional[NodeName]] = Field(
        ...,
        description="Mapping of node -> next node for normal transitions",
        example={"split_text": "generate_summaries"},
    )

    # Conditional edges: node -> {condition_key -> next node or null}
    # e.g. "check_length": {"too_long": "refine_summary", "ok": null}
    conditional_edges: Optional[Dict[NodeName, Dict[str, Optional[NodeName]]]] = Field(
        default_factory=dict,
        description="Optional mapping for branching/looping based on state-derived conditions",
    )


class Graph(BaseModel):
    """
    Internal representation of a stored graph.
    """
    id: GraphId = Field(default_factory=lambda: f"graph_{uuid4().hex}")
    name: str
    entry_node: NodeName
    nodes: List[NodeName]
    edges: Dict[NodeName, Optional[NodeName]]
    conditional_edges: Dict[NodeName, Dict[str, Optional[NodeName]]] = Field(
        default_factory=dict
    )


class GraphCreateResponse(BaseModel):
    """
    Response returned by POST /graph/create.
    """
    graph_id: GraphId


# ---- Run / execution models ----

RunStatus = Literal["pending", "running", "completed", "failed"]


class GraphRunRequest(BaseModel):
    """
    Payload expected by POST /graph/run.
    """
    graph_id: GraphId
    initial_state: State = Field(
        default_factory=dict,
        description="Initial shared state passed to the workflow",
    )


class Run(BaseModel):
    """
    Internal representation of a single execution of a graph.
    Useful for async / long-running workflows.
    """
    id: RunId = Field(default_factory=lambda: f"run_{uuid4().hex}")
    graph_id: GraphId
    status: RunStatus = "pending"

    state: State = Field(default_factory=dict)
    execution_log: List[NodeName] = Field(default_factory=list)

    error: Optional[str] = None


class GraphRunResponse(BaseModel):
    """
    Response returned by POST /graph/run.
    For simplicity assuming synchronous runs that complete in a single request.
    """
    run_id: RunId
    final_state: State
    execution_log: List[NodeName]
    status: RunStatus


class RunStateResponse(BaseModel):
    """
    Response returned by GET /graph/state/{run_id}.
    """
    run_id: RunId
    graph_id: GraphId
    status: RunStatus
    state: State
    execution_log: List[NodeName]
    error: Optional[str] = None

