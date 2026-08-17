"""Execution-engine routing for Learning Publisher code blocks."""

SUPPORTED_ENGINES = {
    ("r", "static"): "r",
    ("r", "r"): "r",
    ("r", "webr"): "webr",
    ("python", "static"): "python",
    ("python", "python"): "python",
    ("python", "pyodide"): "pyodide",
}


def resolve_engine(language: str, mode: str | None = None) -> str:
    """
    Resolve a language/mode pair to a Learning Publisher execution engine.

    Examples:
        ("r", "static") -> "r"
        ("r", "webr") -> "webr"
        ("python", "static") -> "python"
        ("python", "pyodide") -> "pyodide"

    Mode defaults to "static" when omitted.

    Raises:
        ValueError: if the language/mode combination is unsupported.
    """
    normalized_language = (language or "").strip().lower()
    normalized_mode = (mode or "static").strip().lower()

    if not normalized_language:
        raise ValueError("Code block requires a Language value.")

    key = (normalized_language, normalized_mode)

    if key not in SUPPORTED_ENGINES:
        raise ValueError(
            "Unsupported code engine combination: "
            f"Language :: {language}, Mode :: {mode or 'static'}"
        )

    return SUPPORTED_ENGINES[key]
