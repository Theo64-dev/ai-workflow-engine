# app/workflows/summarization.py
"""
Rule-based summarization workflow nodes.

Nodes register themselves using the `@register` decorator from app.registry.
They follow the contract expected by the engine:
- Accept a dict-like `state`
- Mutate and/or return the state
- For conditional nodes, set state[node_name] to a value the engine will read
  (e.g., state["decide_pipeline"] = "short" or "long",
         state["check_length"] = True / False)
"""

from typing import Dict, List
from app.registry import register

# --- Helper utilities ---


def _words(text: str) -> List[str]:
    if not text:
        return []
    return text.split()


def _sentences(text: str) -> List[str]:
    # Naive sentence split by period.
    return [s.strip() for s in text.split(".") if s.strip()]


# --- Nodes ---


@register("decide_pipeline")
def decide_pipeline(state: Dict) -> Dict:
    """
    Decide whether to run the short single-pass pipeline or the full pipeline.
    Sets state["decide_pipeline"] to "short" or "long".

    Decision rule:
    - If original_text word count <= short_threshold -> "short"
    - Else -> "long"
    """
    text = state.get("original_text", "") or ""
    short_threshold = int(state.get("short_threshold", 100))  # words

    wc = len(_words(text))
    state["decide_pipeline"] = "short" if wc <= short_threshold else "long"
    return state


@register("single_pass_summary")
def single_pass_summary(state: Dict) -> Dict:
    """
    Simple one-pass summarizer for short inputs.
    Rule: keep up to `single_pass_words` words (or `max_length` if provided and smaller).
    Produces state["final_summary"].
    """
    text = state.get("original_text", "") or ""
    default_keep = int(state.get("single_pass_words", 80))
    max_len = state.get("max_length")  # optional maximum words for final summary

    keep = default_keep
    if isinstance(max_len, int):
        keep = min(keep, max_len)

    words = _words(text)
    summary_words = words[:keep]
    state["final_summary"] = " ".join(summary_words).strip()
    # iteration counter (useful for logs / safeguards)
    state.setdefault("iteration", 0)
    return state


@register("split_text")
def split_text(state: Dict) -> Dict:
    """
    Split the original_text into word-based chunks.
    - chunk_size: number of words per chunk (default 100)
    Writes state["chunks"] -> List[str]
    """
    text = state.get("original_text", "") or ""
    words = _words(text)
    chunk_size = int(state.get("chunk_size", 100))

    if not words:
        state["chunks"] = []
        return state

    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
    state["chunks"] = chunks
    return state


@register("generate_summaries")
def generate_summaries(state: Dict) -> Dict:
    """
    Produce a simple extractive summary for each chunk.
    Rule: For each chunk, keep first `chunk_summary_words` words.
    Writes state["chunk_summaries"] -> List[str]
    """
    chunks: List[str] = state.get("chunks", []) or []
    chunk_summary_words = int(state.get("chunk_summary_words", 30))

    summaries = []
    for c in chunks:
        words = _words(c)
        summary = " ".join(words[:chunk_summary_words]).strip()
        summaries.append(summary)
    state["chunk_summaries"] = summaries
    return state


@register("merge_summaries")
def merge_summaries(state: Dict) -> Dict:
    """
    Merge chunk summaries into a single `final_summary`.
    Simple concatenation with a space between chunk summaries.
    """
    chunk_summaries: List[str] = state.get("chunk_summaries", []) or []
    merged = " ".join(s for s in chunk_summaries if s).strip()
    state["final_summary"] = merged
    return state


@register("refine_summary")
def refine_summary(state: Dict) -> Dict:
    """
    Refine the current final_summary by trimming it.
    Strategy (rule-based):
    - If summary length <= max_length (if provided) -> do nothing.
    - Else:
        * Reduce the summary length multiplicatively (e.g., 70% of current length),
          but not below max_length if max_length is present.
        * This ensures each iteration reduces size and the loop converges.
    Writes back to state["final_summary"] and increments state["iteration"].
    """
    summary = state.get("final_summary", "") or ""
    if not summary:
        state.setdefault("iteration", 0)
        return state

    words = _words(summary)
    current_len = len(words)
    max_len = state.get("max_length")  # desired target length in words (optional)

    # If no max_len specified, use a conservative default (e.g., 150 words)
    if max_len is None:
        max_len = int(state.get("default_max_length", 150))

    if current_len <= max_len:
        # nothing to do
        state.setdefault("iteration", 0)
        return state

    # reduce multiplicatively to ensure convergence
    reduction_factor = float(state.get("refine_factor", 0.7))  # keep 70% by default
    # compute new length: at least target max_len, or floor(current_len * factor)
    new_len = max(int(current_len * reduction_factor), int(max_len))

    # Safety: ensure we reduce by at least 1 word to avoid zero progress
    if new_len >= current_len:
        new_len = current_len - 1
        if new_len < int(max_len):
            new_len = int(max_len)

    new_summary = " ".join(words[:new_len]).strip()
    state["final_summary"] = new_summary

    # increment iteration counter
    state["iteration"] = int(state.get("iteration", 0)) + 1
    return state


@register("check_length")
def check_length(state: Dict) -> Dict:
    """
    Check if final_summary is longer than max_length.
    Sets state["check_length"] to True if it is too long (engine will loop),
    or False if it's within limits (engine will stop).
    """
    summary = state.get("final_summary", "") or ""
    max_len = state.get("max_length")
    if max_len is None:
        # If no max specified, treat as ok (no loop)
        state["check_length"] = False
        return state

    current_len = len(_words(summary))
    state["check_length"] = current_len > int(max_len)
    return state
