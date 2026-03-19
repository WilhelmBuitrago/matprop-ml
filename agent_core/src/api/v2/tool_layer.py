from dataclasses import dataclass
from typing import Any, Dict, Optional
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError


@dataclass
class ToolResult:
    status: str
    payload_normalized: Any
    validation_flags: Dict[str, bool]
    error_code: Optional[str]
    error_detail: Optional[str]
    elapsed_ms: int


class ToolExecutionLayer:
    def __init__(self, tools: Dict[str, Any], tool_timeout_ms: int = 12000):
        self.tools = tools
        self.tool_timeout_ms = tool_timeout_ms

    def _normalize_payload(self, payload: Any) -> Any:
        if payload is None:
            return {}
        return payload

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        start = int(time.time() * 1000)

        if tool_name not in self.tools:
            return ToolResult(
                status="error",
                payload_normalized={},
                validation_flags={"known_tool": False},
                error_code="TOOL_NOT_FOUND",
                error_detail=f"Unknown tool: {tool_name}",
                elapsed_ms=0,
            )

        tool = self.tools[tool_name]
        if tool is None:
            return ToolResult(
                status="error",
                payload_normalized={},
                validation_flags={"known_tool": True, "executable": False},
                error_code="TOOL_NOT_EXECUTABLE",
                error_detail=f"Tool {tool_name} is control-only",
                elapsed_ms=0,
            )

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(tool.execute, **arguments)
                payload = future.result(timeout=self.tool_timeout_ms / 1000.0)

            elapsed = int(time.time() * 1000) - start
            if elapsed > self.tool_timeout_ms:
                return ToolResult(
                    status="error",
                    payload_normalized=self._normalize_payload(payload),
                    validation_flags={"known_tool": True, "timeout": True},
                    error_code="TOOL_TIMEOUT",
                    error_detail=f"Tool execution exceeded {self.tool_timeout_ms}ms",
                    elapsed_ms=elapsed,
                )

            return ToolResult(
                status="ok",
                payload_normalized=self._normalize_payload(payload),
                validation_flags={"known_tool": True, "timeout": False},
                error_code=None,
                error_detail=None,
                elapsed_ms=elapsed,
            )
        except FutureTimeoutError:
            return ToolResult(
                status="error",
                payload_normalized={},
                validation_flags={"known_tool": True, "timeout": True},
                error_code="TOOL_TIMEOUT",
                error_detail=f"Tool execution exceeded {self.tool_timeout_ms}ms",
                elapsed_ms=int(time.time() * 1000) - start,
            )
        except ValueError as e:
            return ToolResult(
                status="error",
                payload_normalized={},
                validation_flags={"known_tool": True, "input_error": True},
                error_code="TOOL_INPUT_ERROR",
                error_detail=str(e),
                elapsed_ms=int(time.time() * 1000) - start,
            )
        except Exception as e:
            return ToolResult(
                status="error",
                payload_normalized={},
                validation_flags={"known_tool": True, "upstream_error": True},
                error_code="TOOL_UPSTREAM_ERROR",
                error_detail=str(e),
                elapsed_ms=int(time.time() * 1000) - start,
            )
