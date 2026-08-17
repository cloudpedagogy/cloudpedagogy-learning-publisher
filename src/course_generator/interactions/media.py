import re
from urllib.parse import urlparse, parse_qs

import click


def extract_youtube_id(url: str) -> str | None:
    """Extract a YouTube video ID from common YouTube URL formats."""
    url = url.strip()

    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]

    if "youtube.com" in url:
        parsed = urlparse(url)
        return parse_qs(parsed.query).get("v", [None])[0]

    return None

def extract_panopto_id(url: str) -> str | None:
    """Extract the Panopto video/session id from a Panopto Viewer URL."""
    match = re.search(r"[?&]id=([a-zA-Z0-9\-]+)", url)
    return match.group(1) if match else None

def render_youtube_iframe(url: str) -> str:
    """Render a standard YouTube embed iframe from a URL."""
    video_id = extract_youtube_id(url)
    if not video_id:
        return f"<!-- Invalid YouTube URL: {url} -->"

    return (
        f'<iframe width="560" height="315" '
        f'src="https://www.youtube.com/embed/{video_id}" '
        f'title="YouTube video player" frameborder="0" '
        f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
        f'referrerpolicy="strict-origin-when-cross-origin" '
        f'allowfullscreen></iframe>'
    )

def render_panopto_iframe(url: str) -> str:
    """Render a Panopto embed iframe from a Panopto Viewer URL."""
    video_id = extract_panopto_id(url)
    if not video_id:
        return f"<!-- Invalid Panopto URL: {url} -->"

    parsed = urlparse(url)
    embed_url = f"{parsed.scheme}://{parsed.netloc}/Panopto/Pages/Embed.aspx?id={video_id}"

    return (
        f'<iframe src="{embed_url}" title="Panopto video player" width="720" height="405" '
        f'frameborder="0" allowfullscreen></iframe>'
    )

def parse_embeds(content: str) -> tuple[str, int]:
    """
    Parse simple single-line embed directives:

    YouTubeEmbed :: <url>
    PanoptoEmbed :: <url>
    """
    lines = content.split("\n")
    new_lines = []
    count = 0

    for line in lines:
        stripped = line.strip()

        yt_match = re.match(r"^(?:#+\s*)?YouTubeEmbed\s*::\s*(.+)$", stripped, re.IGNORECASE)
        pan_match = re.match(r"^(?:#+\s*)?PanoptoEmbed\s*::\s*(.+)$", stripped, re.IGNORECASE)

        if yt_match:
            url = yt_match.group(1).strip()
            new_lines.append(render_youtube_iframe(url))
            new_lines.append("")
            count += 1
        elif pan_match:
            url = pan_match.group(1).strip()
            new_lines.append(render_panopto_iframe(url))
            new_lines.append("")
            count += 1
        else:
            new_lines.append(line)

    if count > 0:
        click.echo(click.style("Detected video embeds", fg="blue"))
        click.echo(f"  Rendering {count} YouTube/Panopto embeds")

    return "\n".join(new_lines), count

