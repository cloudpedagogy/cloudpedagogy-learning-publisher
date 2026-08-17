import re


def clean_r_code(code: str) -> str:
    """
    Clean R code after Pandoc conversion.

    Fixes:
    - trailing backslashes
    - escaped symbols, including R's native pipe operator
    - artificial blank lines introduced by Word/Pandoc
    """
    cleaned_lines = []

    for raw_line in code.splitlines():
        line = raw_line.rstrip()

        if line.endswith("\\"):
            line = line[:-1].rstrip()

        # Clean escaped R and comparison symbols first.
        line = line.replace(r"\<-", "<-")
        line = line.replace(r"\"", '"')
        line = line.replace(r"\<", "<")
        line = line.replace(r"\>", ">")
        line = line.replace(r"\$", "$")
        line = line.replace(r"\~", "~")
        line = line.replace(r"\#", "#")

        # Run after \> has been converted to >.
        # Supports one or more Pandoc escape backslashes.
        line = re.sub(r"\\+\|>", "|>", line)

        if line.strip():
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()
