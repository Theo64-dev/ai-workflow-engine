# app/registry.py

from typing import Callable, Dict, Any


# ---------------------------------------------------------
# GLOBAL REGISTRY OF NODES (name → Python function)
# ---------------------------------------------------------
NODE_REGISTRY: Dict[str, Callable[[dict], dict]] = {}

# Simple registry for tools (helper functions)
TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {}


# ---------------------------------------------------------
# NODE REGISTRATION DECORATOR
# ---------------------------------------------------------
def register(name: str):
    """
    Decorator to register a Python function as a node in the workflow engine.
    
    Usage:

    @register("split_text")
    def split_text_node(state):
        ...
        return state
    """
    def decorator(func: Callable[[dict], dict]):
        if name in NODE_REGISTRY:
            raise ValueError(f"Node '{name}' is already registered")

        NODE_REGISTRY[name] = func
        return func

    return decorator


# ---------------------------------------------------------
# TOOL REGISTRATION
# ---------------------------------------------------------
def register_tool(name: str):
    """
    Decorator for registering utility functions (tools)
    that nodes may call.
    """
    def decorator(func: Callable[..., Any]):
        if name in TOOL_REGISTRY:
            raise ValueError(f"Tool '{name}' is already registered")

        TOOL_REGISTRY[name] = func
        return func

    return decorator


# ---------------------------------------------------------
# Utility getters
# ---------------------------------------------------------
def get_node(name: str) -> Callable:
    """Get a node function by name, or raise error."""
    if name not in NODE_REGISTRY:
        raise KeyError(f"Node '{name}' is not registered")
    return NODE_REGISTRY[name]


def get_tool(name: str) -> Callable:
    """Get a tool function by name, or raise error."""
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Tool '{name}' is not registered")
    return TOOL_REGISTRY[name]
