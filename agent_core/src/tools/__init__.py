__all__ = [
    "TOOL_REGISTRY",
    "OPENAI_FUNCTION_TOOLS",
    "get_tool_catalog",
]


def __getattr__(name: str):
    if name in {"TOOL_REGISTRY", "OPENAI_FUNCTION_TOOLS", "get_tool_catalog"}:
        from .config import OPENAI_FUNCTION_TOOLS, TOOL_REGISTRY, get_tool_catalog

        exported = {
            "TOOL_REGISTRY": TOOL_REGISTRY,
            "OPENAI_FUNCTION_TOOLS": OPENAI_FUNCTION_TOOLS,
            "get_tool_catalog": get_tool_catalog,
        }
        return exported[name]
    raise AttributeError(f"module 'tools' has no attribute {name!r}")
