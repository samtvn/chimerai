"""
Shared utilities for subagents.
"""


def extract_tool_output(event: dict) -> str:
    """
    Safely extract the string output from an on_tool_end event.
    In astream_events v2, the output may be a ToolMessage object or a plain string.
    """
    raw = event.get("data", {}).get("output", "")
    if hasattr(raw, "content"):
        return str(raw.content)
    return str(raw) if raw is not None else ""
