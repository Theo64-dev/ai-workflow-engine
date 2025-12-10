# app/engine.py
from __future__ import annotations

from typing import Any, Dict, Optional, Callable
from datetime import datetime
import logging

from pydantic import ValidationError

from app import model
from app.model import GraphCreateRequest, Graph, Run, GraphRunResponse, RunStateResponse
from app import registry

logger = logging.getLogger(__name__)


class EngineError(Exception):
    pass


class WorkflowEngine:
    """
    Minimal in-memory workflow engine.
    - stores graphs in self.graphs (graph_id -> Graph)
    - stores runs in self.runs (run_id -> Run)
    - executes graphs synchronously via run_graph()
    """

    def __init__(self, node_registry: Optional[Dict[str, Callable]] = None):
        # allow injecting a registry (useful for tests); default to app.registry.NODE_REGISTRY
        self.node_registry = node_registry if node_registry is not None else registry.NODE_REGISTRY
        self.graphs: Dict[str, Graph] = {}
        self.runs: Dict[str, Run] = {}

    # -------------------------
    # Graph management
    # -------------------------
    def create_graph(self, payload: GraphCreateRequest) -> Graph:
        """
        Validate and store a graph from a GraphCreateRequest.
        """
        # validate nodes exist in registry
        missing = [n for n in payload.nodes if n not in self.node_registry]
        if missing:
            raise EngineError(f"Nodes not found in registry: {missing}")

        # normalize conditional_edges to dict
        conditional_edges = payload.conditional_edges or {}

        graph_obj = Graph(
            name=payload.name,
            entry_node=payload.entry_node,
            nodes=payload.nodes,
            edges=payload.edges,
            conditional_edges=conditional_edges,
        )

        # basic validation: entry_node in nodes
        if graph_obj.entry_node not in graph_obj.nodes:
            raise EngineError(f"entry_node '{graph_obj.entry_node}' is not listed in nodes")

        self.graphs[graph_obj.id] = graph_obj
        logger.info("Graph created: %s", graph_obj.id)
        return graph_obj

    def get_graph(self, graph_id: str) -> Graph:
        g = self.graphs.get(graph_id)
        if g is None:
            raise EngineError(f"Graph not found: {graph_id}")
        return g

    # -------------------------
    # Run management / executor
    # -------------------------
    def run_graph(self, graph_id: str, initial_state: Dict[str, Any], max_iterations: int = 100) -> GraphRunResponse:
        """
        Run the graph synchronously from its entry_node using initial_state.
        Returns a GraphRunResponse with final state and execution log.
        """

        graph = self.get_graph(graph_id)

        # create a Run object and store
        run = Run(graph_id=graph.id, state=initial_state.copy(), status="running", execution_log=[])
        self.runs[run.id] = run

        current_node = graph.entry_node
        iter_count = 0

        try:
            while current_node is not None:
                iter_count += 1
                if iter_count > max_iterations:
                    raise EngineError(f"Max iterations ({max_iterations}) exceeded; possible infinite loop")

                run.execution_log.append(current_node)

                # fetch node function
                node_fn = self.node_registry.get(current_node)
                if node_fn is None:
                    raise EngineError(f"Node function not found in registry: {current_node}")

                # Call node function. Expectation: node modifies state in-place or returns a state dict.
                # Support either pattern: if node returns a dict, we replace run.state; else assume it mutated run.state.
                result = node_fn(run.state)
                if isinstance(result, dict):
                    run.state = result

                # Determine next node
                # 1) If current node is in conditional_edges, use value in state keyed by node name
                if current_node in graph.conditional_edges:
                    cond_map = graph.conditional_edges[current_node]
                    # engine expects the node to set state[current_node] to something (str/bool/int)
                    cond_value = run.state.get(current_node, None)

                    # normalize booleans to "true"/"false" strings for key lookup
                    if isinstance(cond_value, bool):
                        key = "true" if cond_value else "false"
                    elif cond_value is None:
                        # no decision value set by node; fallback: try "default" key if present else error
                        if "default" in cond_map:
                            key = "default"
                        else:
                            raise EngineError(
                                f"Conditional node '{current_node}' did not set state['{current_node}']; "
                                "cannot decide next node"
                            )
                    else:
                        key = str(cond_value)

                    next_node = cond_map.get(key)
                    # if key not present but default provided, use default
                    if next_node is None and "default" in cond_map:
                        next_node = cond_map.get("default")

                    # if still None and key explicitly mapped to null, we stop (next_node None)
                    current_node = next_node
                    continue

                # 2) Otherwise use linear edges mapping
                next_node = graph.edges.get(current_node)
                # If edges mapping doesn't contain current_node => stop after current node
                current_node = next_node

            # finished
            run.status = "completed"
            logger.info("Run %s completed", run.id)

            response = GraphRunResponse(
                run_id=run.id,
                final_state=run.state,
                execution_log=run.execution_log,
                status=run.status,
            )
            return response

        except Exception as e:
            # mark run as failed and surface error
            run.status = "failed"
            run.error = str(e)
            logger.exception("Run %s failed: %s", run.id, e)
            response = GraphRunResponse(
                run_id=run.id,
                final_state=run.state,
                execution_log=run.execution_log,
                status=run.status,
            )
            return response

    def get_run(self, run_id: str) -> Run:
        r = self.runs.get(run_id)
        if r is None:
            raise EngineError(f"Run not found: {run_id}")
        return r

    def get_run_state_response(self, run_id: str) -> RunStateResponse:
        run = self.get_run(run_id)
        return RunStateResponse(
            run_id=run.id,
            graph_id=run.graph_id,
            status=run.status,
            state=run.state,
            execution_log=run.execution_log,
            error=run.error
        )


# default engine instance to import/use from main.py
engine = WorkflowEngine()
