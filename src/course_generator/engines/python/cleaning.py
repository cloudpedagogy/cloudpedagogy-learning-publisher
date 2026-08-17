"""Cleaning helpers for Python code imported from Word/Pandoc."""


def clean_python_code(code: str) -> str:
    """
    Remove narrow Markdown escapes introduced by Word/Pandoc in Python code.

    Stage 4C.1 deliberately fixes only square-bracket escapes observed in
    ordinary Python list/index syntax, for example ``\\[1, 2, 3\\]``.
    It does not broadly remove backslashes, because backslashes may be
    meaningful inside Python strings, regular expressions, or paths.
    """
    return (
        code.replace(r"\[", "[")
            .replace(r"\]", "]")
            .strip()
    )
