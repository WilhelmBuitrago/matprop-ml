from .scheme import CompletionRequestV3, CompletionResponseV3

__all__ = [
    "CompletionRequestV3",
    "CompletionResponseV3",
    "CompletionServiceV3",
]


def __getattr__(name: str):
    if name == "CompletionServiceV3":
        from .service import CompletionServiceV3

        return CompletionServiceV3
    raise AttributeError(f"module 'api.v3' has no attribute {name!r}")
