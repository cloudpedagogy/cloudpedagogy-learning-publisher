import re


def is_markdown_heading(line: str) -> bool:
    return re.match(r"^#+\s+", line.strip()) is not None

def is_interaction_header(line: str) -> bool:
    stripped = line.strip()
    return any(
        re.match(pattern, stripped, re.IGNORECASE)
        for pattern in [
            r"^(?:#+\s*)?R Code\s*$",
            r"^(?:#+\s*)?END R Code\s*$",
            r"^(?:#+\s*)?JavaScript Interaction\s*$",
            r"^(?:#+\s*)?END JavaScript Interaction\s*$",
            r"^(?:#+\s*)?R Example\s*$",
            r"^(?:#+\s*)?END R Example\s*$",
            r"^(?:#+\s*)?Tabs\s*$",
            r"^(?:#+\s*)?END Tabs\s*$",
            r"^(?:#+\s*)?Reveal\s*$",
            r"^(?:#+\s*)?END Reveal\s*$",
            r"^(?:#+\s*)?Quiz\s*$",
            r"^(?:#+\s*)?END Quiz\s*$",
            r"^(?:#+\s*)?SelfCheck\s*$",
            r"^(?:#+\s*)?END SelfCheck\s*$",
            r"^(?:#+\s*)?Callout\s*::",
            r"^(?:#+\s*)?END Callout\s*$",
            r"^(?:#+\s*)?Image\s*::",
            r"^(?:#+\s*)?END Image\s*$",
            r"^(?:#+\s*)?File\s*::",
            r"^(?:#+\s*)?END File\s*$",
            r"^(?:#+\s*)?YouTubeEmbed\s*::",
            r"^(?:#+\s*)?PanoptoEmbed\s*::",
            r"^(?:#+\s*)?HTML Embed\s*::",
            r"^(?:#+\s*)?END HTML Embed\s*$",
        ]
    )
